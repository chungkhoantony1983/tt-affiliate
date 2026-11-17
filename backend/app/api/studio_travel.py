"""
Studio support for travel folders (DR-0002, spec travel-content T-5, T-16, T-17).

A travel folder has topic.json instead of product.json. This module only reads/writes JSON
(C-0001-2): it never imports travel.py or demo.py. Number checks (C-0002-1) and re-voicing run
in the subprocess `demo.py --render-only`, which exits 5 (fact_check) on a wrong number.

Folder data format assumed:
  topic.json  {question, destination, audience, pillar, kind: "travel",
               profile_snapshot: {subtitle_langs: ["vi"], sources: [{domain, ...}], ...}}
  facts.json  [{id, claim, quote, url, source_name, tier, checked_on "YYYY-MM-DD", volatile}]
              (a {"facts": [...]} wrapper is accepted too)
  script.json {hook, caption, hashtags, needs_render, tts_provider,
               segments: [{kind: hook|answer|outro, line, audio_line, text, subs: {lang: str},
                           fact_ids: [...], media: <index into media[]>}],
               media: [{provider, id, page, author, license}]}
"""
import json
import re
import unicodedata
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlsplit

from fastapi import HTTPException

MAX_LINE = 220        # travel line cap (T-18)
MAX_SUB = 220         # one subtitle per scene, per language
MAX_TEXT_WORDS = {"hook": 10, "default": 6}  # on-screen words per scene kind (travel.py: MAX_HOOK_WORDS / MAX_TEXT_WORDS)
FACT_ID = re.compile(r"^[A-Za-z0-9_-]{1,20}$")  # ids end up in a pasted shell command
STALE_DAYS = 30
MAX_FACTS = 50
REPO_ROOT = Path(__file__).resolve().parents[3]
KEEP_SYMBOLS = "°©®™"  # symbols that render fine and appear in real text (25°C)
MAX_FIELD = 600       # cap for any string shown back to the page
PROVIDER_HOSTS = {
    "pixabay": ("pixabay.com",),
    "pexels": ("pexels.com",),
    "wikimedia": ("commons.wikimedia.org",),
}


def is_travel(folder: Path) -> bool:
    return (folder / "topic.json").is_file()


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _write_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _s(value, cap: int = MAX_FIELD) -> str:
    return str(value if value is not None else "")[:cap]


def _host_ok(url: str, domains) -> bool:
    """https only, no userinfo, no custom port, host equals a domain or is a subdomain of it (T-1/T-17)."""
    try:
        parts = urlsplit(url or "")
        host = (parts.hostname or "").lower()
        if parts.scheme != "https" or not host or parts.username or parts.password:
            return False
        if parts.port not in (None, 443):
            return False
    except ValueError:
        return False
    return any(host == d or host.endswith("." + d) for d in domains)


def _snapshot(topic: dict) -> dict:
    snap = topic.get("profile_snapshot")
    return snap if isinstance(snap, dict) else {}


def subtitle_langs(topic: dict) -> List[str]:
    langs = _snapshot(topic).get("subtitle_langs")
    if not isinstance(langs, list):
        return []
    return [l for l in langs if isinstance(l, str) and re.fullmatch(r"[A-Za-z-]{1,10}", l)]


def _source_domains(topic: dict) -> list:
    out = []
    for src in _snapshot(topic).get("sources") or []:
        if isinstance(src, dict) and isinstance(src.get("domain"), str):
            out.append(src["domain"].lower().lstrip("."))
    return out


def _manual_domains(topic: dict) -> list:
    """Domains the code cannot fetch itself (auto_fetch false): their facts need --confirm when refreshed."""
    out = []
    for src in _snapshot(topic).get("sources") or []:
        if isinstance(src, dict) and isinstance(src.get("domain"), str) and src.get("auto_fetch") is False:
            out.append(src["domain"].lower().lstrip("."))
    return out


def check_chars(value: str, label: str) -> None:
    """Reject emoji and other characters the video font cannot draw (400, Vietnamese message)."""
    for ch in value or "":
        cat = unicodedata.category(ch)
        if ord(ch) > 0xFFFF or cat in ("Cc", "Cf", "Cs", "Co", "Cn") or ch == "\ufe0f" \
                or (cat == "So" and ch not in KEEP_SYMBOLS):
            raise HTTPException(status_code=400,
                                detail=f"{label}: có ký tự không hiện được trên video (biểu tượng cảm xúc hoặc ký hiệu lạ). Hãy bỏ ký tự đó")


def _days_old(checked_on) -> Optional[int]:
    try:
        return (date.today() - datetime.strptime(str(checked_on)[:10], "%Y-%m-%d").date()).days
    except ValueError:
        return None


def _is_stale(f: dict) -> bool:
    """Volatile fact checked more than STALE_DAYS ago; a missing/invalid date counts as stale (like travel.stale_facts)."""
    if not f.get("volatile"):
        return False
    age = _days_old(f.get("checked_on"))
    return age is None or age > STALE_DAYS


def _facts(folder: Path, topic: dict) -> tuple:
    raw = _read_json(folder / "facts.json")
    if isinstance(raw, dict):
        raw = raw.get("facts")
    if not isinstance(raw, list):
        raw = []
    domains = _source_domains(topic)
    manual_domains = _manual_domains(topic)
    facts, dropped, stale_ids, confirm_ids, stale_labels = [], 0, [], [], {}
    for f in raw[:MAX_FACTS]:
        if not isinstance(f, dict):
            continue
        fid = str(f.get("id") if f.get("id") is not None else "")
        if not FACT_ID.match(fid):
            dropped += 1
            continue
        if _is_stale(f):
            stale_ids.append(fid)
            stale_labels[fid] = _s(f.get("claim"), 40)
            if f.get("manual") or _host_ok(f.get("url"), manual_domains):
                confirm_ids.append(fid)
        url = f.get("url")
        if not domains:
            # No source list in the snapshot -> the host cannot be checked: show the fact without a link
            dropped += 1
            url = None
        elif not _host_ok(url, domains):
            dropped += 1
            continue
        facts.append({
            "id": fid,
            "claim": _s(f.get("claim")),
            "quote": _s(f.get("quote")),
            "url": url,
            "source_name": _s(f.get("source_name"), 120),
            "tier": f.get("tier") if isinstance(f.get("tier"), int) else None,
            "checked_on": _s(f.get("checked_on"), 10),
            "volatile": bool(f.get("volatile")),
            "stale": _is_stale(f),
            "manual": bool(f.get("manual")),
        })
    return facts, dropped, stale_ids, confirm_ids, stale_labels


def _seg_media(seg: dict) -> list:
    m = seg.get("media")
    items = m if isinstance(m, list) else [m]
    return [i for i in items if isinstance(i, int) and not isinstance(i, bool)]


def _credits(script: dict) -> list:
    scenes = {}
    for n, seg in enumerate(script.get("segments") or [], 1):
        for k in _seg_media(seg):
            scenes.setdefault(k, []).append(n)
    out = []
    for k, m in enumerate(script.get("media") or []):
        if not isinstance(m, dict):
            continue
        provider = str(m.get("provider") or "").lower()
        hosts = PROVIDER_HOSTS.get(provider)
        page = m.get("page")
        out.append({
            "provider": _s(provider, 20),
            "id": _s(m.get("id"), 40),
            "page": page if hosts and _host_ok(page, hosts) else None,
            "author": _s(m.get("author"), 120),
            "license": _s(m.get("license"), 80),
            "scenes": scenes.get(k, []),
        })
    return out


def _subs(seg: dict, langs: List[str]) -> dict:
    raw = seg.get("subs") if isinstance(seg.get("subs"), dict) else {}
    return {l: _s(raw.get(l), 400) for l in langs}


def travel_detail(folder: Path, script: Optional[dict] = None) -> dict:
    """Extra fields merged into the Studio detail of a travel folder."""
    script = script if script is not None else _read_json(folder / "script.json")
    topic = _read_json(folder / "topic.json")
    langs = subtitle_langs(topic)
    facts, dropped, stale_ids, confirm_ids, stale_labels = _facts(folder, topic)
    segments = []
    for i, seg in enumerate(script.get("segments") or []):
        ids = seg.get("fact_ids") if isinstance(seg.get("fact_ids"), list) else []
        segments.append({
            "index": i,
            "kind": seg.get("kind", "answer"),
            "speaker": seg.get("speaker", "narrator"),
            "line": seg.get("line", ""),
            "audio_line": seg.get("audio_line") or seg.get("line", ""),
            "text": seg.get("text", ""),
            "subs": _subs(seg, langs),
            "fact_ids": [_s(x, 40) for x in ids[:20]],
            "image_url": None,
            "image_prompt": "",
        })
    return {
        "kind": "travel",
        "question": _s(topic.get("question")),
        "subtitle_langs": langs,
        "facts": facts,
        "facts_dropped": dropped,
        "stale_ids": stale_ids,
        "stale_labels": stale_labels,
        "confirm_ids": confirm_ids,
        "repo_root": str(REPO_ROOT),
        "credits": _credits(script),
        "segments": segments,
        "price": 0,
        "product_images": [],
    }


def apply_travel_edit(script: dict, topic: dict, edits: Optional[list]) -> bool:
    """Validate and apply per-scene edits (line, text, subs) in place. Returns True if a re-render is needed.
    Raises HTTPException(400) with a Vietnamese message on invalid input. Nothing is written here."""
    if edits is None:
        return False
    segments = script.get("segments") or []
    if len(edits) != len(segments):
        raise HTTPException(status_code=400, detail="Số cảnh không khớp, hãy tải lại trang")
    langs = subtitle_langs(topic)
    staged, needs_render = [], False
    for i, (seg, new) in enumerate(zip(segments, edits)):
        n = i + 1
        line = re.sub(r"\s+", " ", new.line).strip()
        check_chars(line, f"Cảnh {n}: lời đọc")
        check_chars(new.text, f"Cảnh {n}: chữ trên màn hình")
        if not line:
            raise HTTPException(status_code=400, detail=f"Cảnh {n}: lời đọc không được để trống")
        if len(line) > MAX_LINE:
            raise HTTPException(status_code=400, detail=f"Cảnh {n}: lời đọc quá dài (tối đa {MAX_LINE} ký tự)")
        text = re.sub(r"\s+", " ", new.text or "").strip()
        max_words = MAX_TEXT_WORDS.get(seg.get("kind"), MAX_TEXT_WORDS["default"])
        if len(text.split()) > max_words:
            raise HTTPException(status_code=400, detail=f"Cảnh {n}: chữ trên màn hình tối đa {max_words} từ")
        new_subs = {}
        for lang, val in (getattr(new, "subs", None) or {}).items():
            if lang not in langs:
                raise HTTPException(status_code=400, detail=f"Cảnh {n}: không có phụ đề cho ngôn ngữ \"{_s(lang, 12)}\"")
            val = re.sub(r"\s+", " ", val or "").strip()
            check_chars(val, f"Cảnh {n}: phụ đề {lang.upper()}")
            if len(val) > MAX_SUB:
                raise HTTPException(status_code=400, detail=f"Cảnh {n}: phụ đề {lang.upper()} quá dài (tối đa {MAX_SUB} ký tự)")
            new_subs[lang] = val
        staged.append((seg, line, text, new_subs))

    for seg, line, text, new_subs in staged:
        if line != seg.get("line") or text != (seg.get("text") or ""):
            seg.setdefault("audio_line", seg.get("line", ""))
            if seg is segments[0] and line != seg.get("line"):
                script["hook"] = line  # script.hook is a copy of the first line (check_script validates it)
            seg["line"], seg["text"] = line, text
            needs_render = True
        if new_subs:
            cur = seg.get("subs") if isinstance(seg.get("subs"), dict) else {}
            merged = {**cur, **new_subs}
            if merged != cur:
                seg["subs"] = merged
                needs_render = True
    return needs_render
