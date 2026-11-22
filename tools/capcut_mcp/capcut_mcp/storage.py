"""Read and write draft folders inside CapCut's project directory.

Two ways to save:

* **into_existing** (recommended, works on CapCut 8.x / 9.x): the user creates an
  empty project in CapCut, closes CapCut, and we write our timeline into that
  folder. We keep the project's own id, platform and version fields, so CapCut
  sees a project it created itself. Originals are backed up first.
* **new folder**: we create `<drafts_dir>/<name>/` from scratch with CapCut-6-era
  version fields. Older CapCut builds list it after a restart; newer builds may
  refuse it.
"""

from __future__ import annotations

import json
import os
import platform
import re
import shutil
import time
from pathlib import Path

from .draft import US, Draft

CONTENT = "draft_content.json"
LEGACY_CONTENT = "draft_info.json"
META = "draft_meta_info.json"
KEEP_FROM_EXISTING = ("id", "platform", "last_modified_platform", "version", "new_version",
                      "create_time", "name")


class DraftError(RuntimeError):
    pass


def default_drafts_dir() -> Path | None:
    """CapCut desktop's project folder for this OS. CAPCUT_DRAFTS_DIR overrides it."""
    env = os.environ.get("CAPCUT_DRAFTS_DIR")
    if env:
        return Path(env).expanduser()
    system = platform.system()
    if system == "Windows":
        base = os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base) / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft"
    if system == "Darwin":
        return Path.home() / "Movies" / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft"
    return None


def resolve_drafts_dir(drafts_dir: str | None) -> Path:
    d = Path(drafts_dir).expanduser() if drafts_dir else default_drafts_dir()
    if d is None:
        raise DraftError("No CapCut drafts folder on this OS. Set CAPCUT_DRAFTS_DIR or pass drafts_dir.")
    return d


def safe_folder_name(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .")
    return cleaned[:80] or "claude_draft"


def read_json(path: Path) -> dict:
    raw = path.read_bytes()
    try:
        return json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise DraftError(
            f"{path} is not plain JSON. It is probably an encrypted JianYing (剪映) 6+ draft; "
            "this tool only supports CapCut International drafts.") from e


def write_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp-claude")
    tmp.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    os.replace(tmp, path)


def _find_folder(drafts_root: Path, ref: str) -> Path:
    p = Path(ref).expanduser()
    if p.is_absolute() or p.exists():
        if (p / CONTENT).exists() or (p / META).exists():
            return p
        raise DraftError(f"{p} is not a CapCut draft folder (no {CONTENT} / {META})")
    cand = drafts_root / ref
    if cand.is_dir():
        return cand
    for d in drafts_root.iterdir() if drafts_root.is_dir() else []:
        meta = d / META
        if meta.is_file():
            try:
                m = read_json(meta)
            except DraftError:
                continue
            if m.get("draft_name") == ref or m.get("draft_id") == ref:
                return d
    raise DraftError(f"No CapCut project named {ref!r} in {drafts_root}")


def _merge_content(existing: dict, ours: dict) -> dict:
    merged = dict(existing)
    for k, v in ours.items():
        if k in KEEP_FROM_EXISTING and k in existing:
            continue
        if k == "materials":
            mats = {key: [] for key, val in existing.get("materials", {}).items() if isinstance(val, list)}
            for key, val in existing.get("materials", {}).items():
                if not isinstance(val, list):
                    mats[key] = val
            mats.update(v)
            merged[k] = mats
        elif k == "keyframes":
            merged[k] = {key: [] for key in existing.get("keyframes", {})} | v
        elif k == "config" and isinstance(existing.get("config"), dict):
            merged[k] = existing["config"]
        else:
            merged[k] = v
    return merged


def _copy_media(draft: Draft, folder: Path) -> None:
    dest = folder / "materials"
    dest.mkdir(parents=True, exist_ok=True)
    seen: dict[str, str] = {}
    for m in draft.materials["videos"] + draft.materials["audios"]:
        src = Path(m["path"])
        if str(src) in seen:
            m["path"] = seen[str(src)]
            continue
        target = dest / src.name
        n = 1
        while target.exists() and not _same_file(src, target):
            target = dest / f"{src.stem}_{n}{src.suffix}"
            n += 1
        if not target.exists():
            shutil.copy2(src, target)
        seen[str(src)] = str(target.resolve())
        m["path"] = seen[str(src)]


def _same_file(a: Path, b: Path) -> bool:
    try:
        return a.stat().st_size == b.stat().st_size and a.read_bytes() == b.read_bytes()
    except OSError:
        return False


def save_draft(draft: Draft, drafts_dir: str | None = None, into_existing: str | None = None,
               overwrite: bool = False, copy_media: bool = False,
               allow_missing_media: bool = False) -> dict:
    """Write the draft. Returns {folder, mode, files, warnings}."""
    problems = draft.validate()
    missing = [p for p in problems if p.startswith("Media file missing")]
    hard = [p for p in problems if p not in missing]
    if hard:
        raise DraftError("Draft is not valid: " + "; ".join(hard))
    if missing and not allow_missing_media:
        raise DraftError("; ".join(missing) + " (pass allow_missing_media=true if the files "
                         "exist only on the machine that will open the draft)")
    root = resolve_drafts_dir(drafts_dir)
    warnings: list[str] = list(missing)
    written: list[str] = []
    stamp = time.strftime("%Y%m%d-%H%M%S")

    if into_existing:
        folder = _find_folder(root, into_existing)
        if copy_media:
            _copy_media(draft, folder)
        content_path = folder / CONTENT
        existing = read_json(content_path) if content_path.exists() else {}
        if existing.get("id"):
            draft.id = existing["id"]
        ours = draft.to_content()
        merged = _merge_content(existing, ours) if existing else ours
        targets = [content_path]
        if (folder / LEGACY_CONTENT).exists():
            targets.append(folder / LEGACY_CONTENT)
        timelines = folder / "Timelines"
        if timelines.is_dir():
            for sub in timelines.iterdir():
                for fn in (CONTENT, LEGACY_CONTENT):
                    if (sub / fn).is_file():
                        targets.append(sub / fn)
        for path in targets:
            if path.exists():
                shutil.copy2(path, path.with_name(path.name + f".bak-{stamp}"))
            data = merged
            if path != content_path and path.exists():
                try:
                    data = _merge_content(read_json(path), ours)
                except DraftError:
                    pass
            write_json(path, data)
            written.append(str(path))
        meta_path = folder / META
        if meta_path.exists():
            meta = read_json(meta_path)
            shutil.copy2(meta_path, meta_path.with_name(META + f".bak-{stamp}"))
            meta["tm_duration"] = draft.duration_us
            meta["tm_draft_modified"] = int(time.time() * US)
        else:
            meta = draft.to_meta(str(folder), str(root))
        write_json(meta_path, meta)
        written.append(str(meta_path))
        if len(targets) > 1:
            warnings.append(f"Also wrote {len(targets) - 1} mirror timeline file(s) used by newer CapCut")
        return {"folder": str(folder), "mode": "into_existing", "draft_id": draft.id,
                "files": written, "warnings": warnings}

    root.mkdir(parents=True, exist_ok=True)
    folder = root / safe_folder_name(draft.name)
    if folder.exists():
        if not overwrite:
            raise DraftError(f"{folder} already exists. Pick another name or pass overwrite=true.")
        if not (folder / META).exists() and any(folder.iterdir()):
            raise DraftError(f"{folder} exists and is not a CapCut draft; refusing to overwrite.")
        backup = folder.with_name(folder.name + f".bak-{stamp}")
        shutil.move(str(folder), backup)
        warnings.append(f"Previous folder moved to {backup}")
    folder.mkdir(parents=True)
    if copy_media:
        _copy_media(draft, folder)
    content = draft.to_content()
    write_json(folder / CONTENT, content)
    write_json(folder / LEGACY_CONTENT, content)
    write_json(folder / META, draft.to_meta(str(folder), str(root)))
    written = [str(folder / CONTENT), str(folder / LEGACY_CONTENT), str(folder / META)]
    warnings.append("Restart CapCut to see the new project. If CapCut 8.7+/9.x refuses it, "
                    "create an empty project in CapCut, close CapCut, and save with into_existing.")
    return {"folder": str(folder), "mode": "new", "draft_id": draft.id, "files": written,
            "warnings": warnings}


def list_drafts(drafts_dir: str | None = None) -> list[dict]:
    root = resolve_drafts_dir(drafts_dir)
    if not root.is_dir():
        raise DraftError(f"Drafts folder does not exist: {root}")
    out = []
    for d in sorted(root.iterdir()):
        meta_path = d / META
        if not d.is_dir() or not meta_path.is_file():
            continue
        try:
            meta = read_json(meta_path)
        except DraftError:
            meta = {}
        content_ok = None
        if (d / CONTENT).is_file():
            try:
                read_json(d / CONTENT)
                content_ok = True
            except DraftError:
                content_ok = False
        out.append({
            "folder": d.name, "name": meta.get("draft_name", d.name),
            "draft_id": meta.get("draft_id"),
            "duration": (meta.get("tm_duration") or 0) / US,
            "modified": time.strftime("%Y-%m-%d %H:%M",
                                      time.localtime((meta.get("tm_draft_modified") or 0) / US)),
            "readable": content_ok,
        })
    return out


def inspect_draft(ref: str, drafts_dir: str | None = None) -> dict:
    """Summarise an existing draft and list reusable library resources (transitions,
    effects, filters, text animations) with their ids."""
    root = resolve_drafts_dir(drafts_dir)
    folder = _find_folder(root, ref)
    content = read_json(folder / CONTENT)
    mats = content.get("materials", {})
    by_id = {m.get("id"): (k, m) for k, lst in mats.items() if isinstance(lst, list)
             for m in lst if isinstance(m, dict)}
    tracks = []
    for t in content.get("tracks", []):
        segs = []
        for s in t.get("segments", []):
            tr = s.get("target_timerange") or {}
            kind, m = by_id.get(s.get("material_id"), ("?", {}))
            label = m.get("material_name") or m.get("name") or ""
            if kind == "texts":
                try:
                    label = json.loads(m.get("content", "{}")).get("text", "")[:40]
                except json.JSONDecodeError:
                    pass
            segs.append({"start": tr.get("start", 0) / US,
                         "end": (tr.get("start", 0) + tr.get("duration", 0)) / US,
                         "material": kind, "label": label})
        tracks.append({"type": t.get("type"), "name": t.get("name"), "segments": segs})

    def pick(kind: str, fields: tuple[str, ...]) -> list[dict]:
        seen, out = set(), []
        for m in mats.get(kind, []) or []:
            key = m.get("resource_id") or m.get("effect_id") or m.get("id")
            if key in seen:
                continue
            seen.add(key)
            out.append({f: m.get(f) for f in fields if f in m})
        return out

    res_fields = ("name", "effect_id", "resource_id", "category_id", "category_name", "duration",
                  "is_overlap", "path")
    return {
        "folder": str(folder), "name": content.get("name"),
        "app_version": (content.get("platform") or {}).get("app_version"),
        "version": content.get("version"), "new_version": content.get("new_version"),
        "canvas": content.get("canvas_config"), "duration": (content.get("duration") or 0) / US,
        "tracks": tracks,
        "reusable": {
            "transitions": pick("transitions", res_fields),
            "video_effects": pick("video_effects", res_fields),
            "effects": pick("effects", res_fields),
            "material_animations": [a for a in (mats.get("material_animations") or []) if a.get("animations")],
        },
    }
