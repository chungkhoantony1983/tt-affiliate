"""Turn a video spec into a CapCut draft project using pycapcut."""

from __future__ import annotations

import difflib
import json
import shutil
import time
import uuid
from pathlib import Path
from typing import Any

import pycapcut as cc
from pycapcut import (ClipSettings, KeyframeProperty, TextBackground, TextBorder,
                      TextShadow, TextStyle, TrackType)

from .common import (ASPECTS, POSITIONS, fetch_media, get_drafts_folder, hex_to_rgb01,
                     is_video, normalise_spec, safe_name, solid_color_png)

SEC = 1_000_000

# Friendly English aliases -> CapCut internal effect names.
ALIASES: dict[str, dict[str, str]] = {
    "transition": {
        "dissolve": "叠化", "fade": "叠化", "slide_left": "向左", "slide_up": "向上",
        "flash_white": "闪白", "flash_black": "闪黑", "push_in": "推近", "pull_out": "拉远",
        "page_turn": "翻页", "glitch": "色差顺时针", "move_left": "左移", "move_right": "右移",
        "white_flash": "White_Flash", "fold": "Fold_Over", "light_beam": "光束",
    },
    "clip_in": {"fade": "渐显", "zoom": "放大", "shrink": "缩小", "slide_left": "向左滑动",
                "slide_right": "向右滑动", "slide_up": "向上滑动", "dynamic_zoom": "动感放大",
                "shake": "轻微抖动"},
    "clip_out": {"fade": "渐隐", "shrink": "缩小", "zoom": "放大", "slide_left": "向左滑动"},
    "text_in": {"pop": "弹出", "typewriter": "打字机_I", "fade": "渐显", "zoom": "放大",
                "slide_up": "向上滑动", "slide_left": "向左滑动", "bounce": "弹入",
                "glitch": "故障", "shine": "扫光入场", "punch": "冲屏位移"},
    "text_out": {"fade": "渐隐", "shrink": "缩小", "slide_down": "向下滑动", "blur": "模糊"},
    "text_loop": {"pulse": "闪动脉冲", "shake": "晃动", "heartbeat": "心跳频闪", "float": "漂浮",
                  "wave": "波浪", "zoom_letters": "逐字放大", "playful": "调皮"},
}

ENUMS = {
    "transition": cc.TransitionType, "clip_in": cc.IntroType, "clip_out": cc.OutroType,
    "text_in": cc.TextIntro, "text_out": cc.TextOutro, "text_loop": cc.TextLoopAnim,
    "font": cc.FontType, "filter": cc.FilterType, "scene_effect": cc.VideoSceneEffectType,
}


def resolve(kind: str, name: str | None):
    if not name:
        return None
    enum = ENUMS[kind]
    key = ALIASES.get(kind, {}).get(name, name)
    if key in enum.__members__:
        return enum[key]
    lowered = {k.lower(): k for k in enum.__members__}
    if key.lower() in lowered:
        return enum[lowered[key.lower()]]
    close = difflib.get_close_matches(key, list(enum.__members__) + list(ALIASES.get(kind, {})), n=6)
    raise ValueError(f"Không có {kind} tên '{name}'. Gợi ý: {close}. Dùng tool list_effects để tra.")


def list_effect_names(kind: str, query: str = "", limit: int = 80) -> dict[str, Any]:
    enum = ENUMS[kind]
    names = [n for n in enum.__members__ if query.lower() in n.lower()]
    return {"kind": kind, "aliases": ALIASES.get(kind, {}), "total": len(names), "names": names[:limit]}


def _write_meta(draft_dir: Path, name: str, duration_us: int, root: Path) -> None:
    meta_path = draft_dir / "draft_meta_info.json"
    meta = json.loads(meta_path.read_text("utf-8"))
    now_us = int(time.time() * SEC)
    meta.update({
        "draft_id": str(uuid.uuid4()).upper(),
        "draft_name": name,
        "draft_fold_path": str(draft_dir).replace("\\", "/"),
        "draft_root_path": str(root).replace("\\", "/"),
        "tm_draft_create": now_us,
        "tm_draft_modified": now_us,
        "tm_duration": duration_us,
    })
    meta_path.write_text(json.dumps(meta, ensure_ascii=False), "utf-8")


SKELETON = Path(__file__).parent / "skeleton_v9"


def _to_v9_layout(draft_dir: Path, name: str, duration_us: int, root: Path) -> None:
    """CapCut 9.x (Mac) lists a draft only with draft_info.json + Timelines/ layout.

    pycapcut writes the older draft_content.json layout; wrap it in the skeleton of an
    empty draft saved by CapCut 9.8 and keep draft_content.json for older versions.
    """
    shutil.copytree(SKELETON, draft_dir, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("_timeline"))
    ref = json.loads((SKELETON / "draft_info.json").read_text("utf-8"))
    content = json.loads((draft_dir / "draft_content.json").read_text("utf-8"))
    for k in set(ref) - set(content):
        content[k] = ref[k]
    tl, proj_id = str(uuid.uuid4()).upper(), str(uuid.uuid4()).upper()
    content.update(id=tl, new_version=ref["new_version"], platform=ref["platform"],
                   last_modified_platform=ref.get("last_modified_platform", ref["platform"]))
    txt = json.dumps(content, ensure_ascii=False)
    (draft_dir / "draft_info.json").write_text(txt, "utf-8")
    # A timeline folder without CapCut's attachment files opens as an empty timeline.
    shutil.copytree(SKELETON / "Timelines" / "_timeline", draft_dir / "Timelines" / tl)
    (draft_dir / "Timelines" / tl / "draft_info.json").write_text(txt, "utf-8")
    now_us = int(time.time() * SEC)
    proj = json.loads((SKELETON / "Timelines/project.json").read_text("utf-8"))
    proj.update(id=proj_id, main_timeline_id=tl, create_time=now_us, update_time=now_us)
    proj["timelines"] = [dict(proj["timelines"][0], id=tl, create_time=now_us, update_time=now_us)]
    (draft_dir / "Timelines/project.json").write_text(json.dumps(proj), "utf-8")
    lay = json.loads((SKELETON / "timeline_layout.json").read_text("utf-8"))
    lay["dockItems"][0]["timelineIds"] = [tl]
    (draft_dir / "timeline_layout.json").write_text(json.dumps(lay), "utf-8")
    meta = json.loads((SKELETON / "draft_meta_info.json").read_text("utf-8"))
    meta.update(draft_id=str(uuid.uuid4()).upper(), draft_name=name,
                draft_fold_path=str(draft_dir), draft_root_path=str(root),
                tm_draft_create=now_us, tm_draft_modified=now_us, tm_duration=duration_us)
    (draft_dir / "draft_meta_info.json").write_text(json.dumps(meta, ensure_ascii=False), "utf-8")


def _copy_in(src: Path, assets: Path, idx: int) -> Path:
    assets.mkdir(exist_ok=True)
    dst = assets / f"{idx:02d}_{safe_name(src.stem)}{src.suffix.lower()}"
    if not dst.exists():
        shutil.copy2(src, dst)
    return dst


def _motion(seg: cc.VideoSegment, motion: str, dur: int) -> None:
    if motion in (None, "none"):
        return
    if motion == "zoom_in":
        seg.add_keyframe(KeyframeProperty.uniform_scale, 0, 1.0)
        seg.add_keyframe(KeyframeProperty.uniform_scale, dur, 1.15)
    elif motion == "zoom_out":
        seg.add_keyframe(KeyframeProperty.uniform_scale, 0, 1.15)
        seg.add_keyframe(KeyframeProperty.uniform_scale, dur, 1.0)
    elif motion in ("pan_left", "pan_right"):
        sign = -1 if motion == "pan_left" else 1
        seg.add_keyframe(KeyframeProperty.uniform_scale, 0, 1.15)
        seg.add_keyframe(KeyframeProperty.position_x, 0, -0.06 * sign)
        seg.add_keyframe(KeyframeProperty.position_x, dur, 0.06 * sign)
    else:
        raise ValueError(f"motion không hợp lệ: {motion} (zoom_in|zoom_out|pan_left|pan_right|none)")


def _text_segment(t: dict[str, Any], start_us: int, scene_dur_us: int, aspect: str) -> cc.TextSegment:
    t_start = start_us + int(float(t["start"]) * SEC)
    t_end = start_us + min(int(float(t["end"]) * SEC), scene_dur_us)
    style = TextStyle(size=float(t["size"]), bold=bool(t["bold"]), color=hex_to_rgb01(t["color"]),
                      align=1, auto_wrapping=True, max_line_width=0.86)
    y = t.get("y", POSITIONS.get(t["position"], -0.68))
    kwargs: dict[str, Any] = {"style": style, "clip_settings": ClipSettings(transform_y=float(y))}
    if t.get("font"):
        kwargs["font"] = resolve("font", t["font"])
    if t.get("bg"):
        kwargs["background"] = TextBackground(color=t["bg"], style=1, alpha=float(t.get("bg_alpha", 0.9)),
                                              round_radius=0.4, height=0.2, width=0.2)
    if t.get("border"):
        kwargs["border"] = TextBorder(color=hex_to_rgb01(t["border"]), width=float(t.get("border_width", 40)))
    if t.get("shadow", not t.get("bg")):
        kwargs["shadow"] = TextShadow(alpha=0.6)
    seg = cc.TextSegment(t["text"], cc.Timerange(t_start, max(t_end - t_start, SEC // 5)), **kwargs)
    for kind in ("text_in", "text_out", "text_loop"):
        anim = resolve(kind, t.get(kind))
        if anim is not None:
            seg.add_animation(anim)
    return seg


def build_capcut_draft(spec: dict[str, Any], *, overwrite: bool = True,
                       drafts_folder: str | None = None) -> dict[str, Any]:
    spec = normalise_spec(spec)
    root = Path(drafts_folder) if drafts_folder else get_drafts_folder()
    if root is None or not root.is_dir():
        raise FileNotFoundError(
            "Không tìm thấy thư mục draft của CapCut. Hãy mở CapCut, tạo 1 dự án trống, "
            "hoặc gọi tool set_drafts_folder với đường dẫn đúng.")
    width, height = ASPECTS[spec["aspect"]]
    name = safe_name(spec["name"])
    folder = cc.DraftFolder(str(root))
    script = folder.create_draft(name, width, height, fps=int(spec["fps"]), allow_replace=overwrite)
    draft_dir = root / name
    assets = draft_dir / "assets"

    script.add_track(TrackType.video, "main")
    max_texts = max((len(sc["texts"]) for sc in spec["scenes"]), default=0)
    for i in range(max_texts):
        script.add_track(TrackType.text, f"text_{i}")

    cursor = 0
    segments: list[cc.VideoSegment] = []
    for i, sc in enumerate(spec["scenes"]):
        dur = int(sc["duration"] * SEC)
        media = fetch_media(sc["media"]) if sc.get("media") else solid_color_png(sc["background"], width, height)
        media = _copy_in(media, assets, i)
        material = cc.VideoMaterial(str(media))
        if is_video(media):
            src_dur = min(dur, material.duration)
            dur = src_dur
            seg = cc.VideoSegment(material, cc.Timerange(cursor, dur),
                                  source_timerange=cc.Timerange(int(sc.get("trim_start", 0) * SEC), dur),
                                  volume=float(sc.get("volume", 0.0)))
        else:
            seg = cc.VideoSegment(material, cc.Timerange(cursor, dur))
            _motion(seg, sc["motion"], dur)
        seg.add_background_filling("blur", 0.375)
        if sc.get("clip_in"):
            seg.add_animation(resolve("clip_in", sc["clip_in"]))
        if sc.get("filter"):
            seg.add_filter(resolve("filter", sc["filter"]), float(sc.get("filter_intensity", 80)))
        if sc.get("transition") and i < len(spec["scenes"]) - 1:
            seg.add_transition(resolve("transition", sc["transition"]))
        script.add_segment(seg, "main")
        segments.append(seg)
        for j, t in enumerate(sc["texts"]):
            script.add_segment(_text_segment(t, cursor, dur, spec["aspect"]), f"text_{j}")
        cursor += dur
    total = cursor

    for track_name, key in (("music", "music"), ("voice", "voiceover")):
        audio = spec.get(key)
        if not audio:
            continue
        if isinstance(audio, str):
            audio = {"path": audio}
        apath = _copy_in(fetch_media(audio["path"]), assets, 90 if key == "music" else 91)
        amat = cc.AudioMaterial(str(apath))
        script.add_track(TrackType.audio, track_name)
        vol = float(audio.get("volume", 0.35 if key == "music" else 1.0))
        pos = 0
        first = True
        while pos < total:
            chunk = min(amat.duration, total - pos)
            aseg = cc.AudioSegment(amat, cc.Timerange(pos, chunk), volume=vol)
            if key == "music" and (first or pos + chunk >= total):
                aseg.add_fade("0.5s" if first else "0s", "1s" if pos + chunk >= total else "0s")
            script.add_segment(aseg, track_name)
            pos += chunk
            first = False
            if key == "voiceover":
                break

    script.save()
    _write_meta(draft_dir, name, total, root)
    _to_v9_layout(draft_dir, name, total, root)
    return {"draft_name": name, "draft_path": str(draft_dir), "duration_s": round(total / SEC, 2),
            "scenes": len(spec["scenes"]), "size": f"{width}x{height}"}
