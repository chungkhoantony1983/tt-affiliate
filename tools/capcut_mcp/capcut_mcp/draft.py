"""Build a CapCut desktop draft (international CapCut, unencrypted JSON) in memory.

The draft format is undocumented. Field names and defaults follow the open-source
references pyJianYingDraft / pyCapCut / capcut-cli (see README "Sources"):

* all times are integer microseconds (1 s = 1_000_000);
* `tracks[].segments[]` point at `materials.<kind>[]` through `material_id`, and at
  helper materials (speed, canvas, sound channel, fades, transitions) through
  `extra_material_refs`;
* positions (`clip.transform`) are normalised to [-1, 1], (0, 0) = centre,
  y = -1 is the bottom edge.

The public API takes seconds; conversion happens here.
"""

from __future__ import annotations

import copy
import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .media import MediaInfo, kind_from_ext, probe
from .srt import parse_srt

US = 1_000_000
PHOTO_MATERIAL_DURATION = 10_800 * US  # CapCut gives stills a 3-hour source
DEFAULT_PHOTO_SECONDS = 3.0

# Version fields of a CapCut 6.x-era draft. When writing into a project that
# CapCut itself created (recommended), storage.py keeps that project's values.
DEFAULT_VERSION = 360000
DEFAULT_NEW_VERSION = "110.0.0"
DEFAULT_PLATFORM = {
    "app_id": 359289,
    "app_source": "cc",
    "app_version": "6.5.0",
    "device_id": "",
    "hard_disk_id": "",
    "mac_address": "",
    "os": "windows",
    "os_version": "",
}

MATERIAL_KINDS = (
    "audio_balances", "audio_effects", "audio_fades", "audio_track_indexes", "audios",
    "beats", "canvases", "chromas", "color_curves", "digital_humans", "drafts", "effects",
    "flowers", "green_screens", "handwrites", "hsl", "images", "log_color_wheels", "loudnesses",
    "manual_deformations", "masks", "material_animations", "material_colors",
    "multi_language_refs", "placeholders", "plugin_effects", "primary_color_wheels",
    "realtime_denoises", "shapes", "smart_crops", "smart_relights", "sound_channel_mappings",
    "speeds", "stickers", "tail_leaders", "text_templates", "texts", "time_marks",
    "transitions", "video_effects", "video_trackings", "videos", "vocal_beautifys",
    "vocal_separations",
)
KEYFRAME_KINDS = ("adjusts", "audios", "effects", "filters", "handwrites", "stickers", "texts", "videos")
TRACK_TYPES = ("video", "audio", "text")


def new_id() -> str:
    return str(uuid.uuid4()).upper()


def to_us(seconds: float) -> int:
    return int(round(float(seconds) * US))


def hex_to_rgb(color: str) -> list[float]:
    c = color.strip().lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    if len(c) != 6:
        raise ValueError(f"Colour must be #RRGGBB, got {color!r}")
    return [round(int(c[i:i + 2], 16) / 255, 6) for i in (0, 2, 4)]


def utf16_len(text: str) -> int:
    """CapCut text style ranges count UTF-16 code units (matters for emoji)."""
    return len(text.encode("utf-16-le")) // 2


# --------------------------------------------------------------------------- #
# Helper materials
# --------------------------------------------------------------------------- #

def _speed(speed: float) -> dict:
    return {"curve_speed": None, "id": new_id(), "mode": 0, "speed": speed, "type": "speed"}


def _canvas() -> dict:
    return {"album_image": "", "blur": 0.0, "color": "", "id": new_id(), "image": "",
            "image_id": "", "image_name": "", "source_platform": 0, "team_id": "",
            "type": "canvas_color"}


def _sound_channel() -> dict:
    return {"audio_channel_mapping": 0, "id": new_id(), "is_config_open": False, "type": ""}


def _audio_fade(fade_in: float, fade_out: float) -> dict:
    return {"fade_in_duration": to_us(fade_in), "fade_out_duration": to_us(fade_out),
            "fade_type": 0, "id": new_id(), "type": "audio_fade"}


def _keyframe(prop: str, points: list[tuple[int, float]]) -> dict:
    return {
        "id": new_id(),
        "keyframe_list": [
            {"curveType": "Line", "graphID": "", "id": new_id(),
             "left_control": {"x": 0.0, "y": 0.0}, "right_control": {"x": 0.0, "y": 0.0},
             "time_offset": t, "values": [v]}
            for t, v in points
        ],
        "material_id": "",
        "property_type": prop,
    }


def _clip(scale: float = 1.0, x: float = 0.0, y: float = 0.0, alpha: float = 1.0) -> dict:
    return {"alpha": alpha, "flip": {"horizontal": False, "vertical": False}, "rotation": 0.0,
            "scale": {"x": scale, "y": scale}, "transform": {"x": x, "y": y}}


def _base_segment(material_id: str, start_us: int, dur_us: int, src_start_us: int,
                  src_dur_us: int | None, speed: float, volume: float,
                  extra_refs: list[str], render_index: int) -> dict:
    return {
        "caption_info": None, "cartoon": False, "clip": _clip(), "common_keyframes": [],
        "enable_adjust": True, "enable_color_correct_adjust": False,
        "enable_color_curves": True, "enable_color_match_adjust": False,
        "enable_color_wheels": True, "enable_lut": True, "enable_smart_color_adjust": False,
        "extra_material_refs": extra_refs, "group_id": "",
        "hdr_settings": {"intensity": 1.0, "mode": 1, "nits": 1000}, "id": new_id(),
        "intensifies_audio": False, "is_placeholder": False, "is_tone_modify": False,
        "keyframe_refs": [], "last_nonzero_volume": 1.0, "material_id": material_id,
        "render_index": render_index, "responsive_layout": {
            "enable": False, "horizontal_pos_layout": 0, "size_layout": 0,
            "target_follow": "", "vertical_pos_layout": 0},
        "reverse": False,
        "source_timerange": None if src_dur_us is None else {"duration": src_dur_us, "start": src_start_us},
        "speed": speed, "target_timerange": {"duration": dur_us, "start": start_us},
        "template_id": "", "template_scene": "default", "track_attribute": 0,
        "track_render_index": 0, "uniform_scale": {"on": True, "value": 1.0},
        "visible": True, "volume": volume,
    }


# --------------------------------------------------------------------------- #
# Draft
# --------------------------------------------------------------------------- #

@dataclass
class Track:
    type: str
    name: str
    render_index: int
    id: str = field(default_factory=new_id)
    segments: list[dict] = field(default_factory=list)

    def end_us(self) -> int:
        return max((s["target_timerange"]["start"] + s["target_timerange"]["duration"]
                    for s in self.segments), default=0)

    def to_json(self) -> dict:
        segs = sorted(self.segments, key=lambda s: s["target_timerange"]["start"])
        return {"attribute": 0, "flag": 0, "id": self.id, "is_default_name": False,
                "name": self.name, "segments": segs, "type": self.type}


class Draft:
    """An in-memory CapCut timeline. Times in the public methods are seconds."""

    def __init__(self, name: str, width: int = 1080, height: int = 1920, fps: float = 30.0,
                 draft_id: str | None = None):
        if width <= 0 or height <= 0:
            raise ValueError("width/height must be positive")
        if fps <= 0:
            raise ValueError("fps must be positive")
        self.name = name
        self.width = int(width)
        self.height = int(height)
        self.fps = float(fps)
        self.id = draft_id or new_id()
        self.tracks: list[Track] = []
        self.materials: dict[str, list[dict]] = {k: [] for k in MATERIAL_KINDS}
        self.created_us = int(time.time() * US)

    # ---- tracks ---------------------------------------------------------- #

    def track(self, name: str) -> Track:
        for t in self.tracks:
            if t.name == name:
                return t
        raise KeyError(f"No track named {name!r}. Existing: {[t.name for t in self.tracks]}")

    def ensure_track(self, kind: str, name: str) -> Track:
        if kind not in TRACK_TYPES:
            raise ValueError(f"track type must be one of {TRACK_TYPES}")
        for t in self.tracks:
            if t.name == name:
                if t.type != kind:
                    raise ValueError(f"Track {name!r} is a {t.type} track, not {kind}")
                return t
        same = [t for t in self.tracks if t.type == kind]
        base = {"video": 0, "audio": 0, "text": 15000}[kind]
        t = Track(type=kind, name=name, render_index=base + len(same))
        self.tracks.append(t)
        return t

    def _place(self, track: Track, start: float | None, dur_us: int) -> int:
        start_us = track.end_us() if start is None else to_us(start)
        if start_us < 0:
            raise ValueError("start must be >= 0")
        if dur_us <= 0:
            raise ValueError("duration must be > 0")
        end_us = start_us + dur_us
        for s in track.segments:
            a = s["target_timerange"]["start"]
            b = a + s["target_timerange"]["duration"]
            if start_us < b and a < end_us:
                raise ValueError(
                    f"Overlaps an existing segment on track {track.name!r} "
                    f"({a / US:.3f}s-{b / US:.3f}s). Use another track or start time.")
        return start_us

    # ---- visual media ---------------------------------------------------- #

    def add_media(self, path: str, start: float | None = None, duration: float | None = None,
                  source_start: float = 0.0, track: str = "main", volume: float = 1.0,
                  speed: float = 1.0, scale: float = 1.0, x: float = 0.0, y: float = 0.0,
                  fade_in: float = 0.0, fade_out: float = 0.0,
                  zoom_from: float | None = None, zoom_to: float | None = None,
                  info: MediaInfo | None = None) -> dict:
        """Add a video clip or a still image to a video track.

        start=None appends after the last segment of the track. For videos, duration
        defaults to (file length - source_start) / speed. For photos, to 3 s.
        fade_in/fade_out use opacity keyframes; zoom_from/zoom_to add a slow
        Ken Burns scale animation (e.g. 1.0 -> 1.15).
        """
        kind = kind_from_ext(path)
        if kind == "audio":
            raise ValueError("Audio files go through add_audio")
        if speed <= 0:
            raise ValueError("speed must be > 0")
        info = info or _safe_probe(path, kind)
        abs_path = str(Path(path).expanduser().resolve())
        t = self.ensure_track("video", track)

        if kind == "photo":
            dur_us = to_us(duration if duration is not None else DEFAULT_PHOTO_SECONDS)
            src_us, src_dur_us = 0, dur_us
            mat_duration = PHOTO_MATERIAL_DURATION
            speed = 1.0
        else:
            if info.duration is None and duration is None:
                raise ValueError(f"Cannot read the length of {path}; pass duration explicitly")
            src_us = to_us(source_start)
            if info.duration is not None:
                available = to_us(info.duration) - src_us
                if available <= 0:
                    raise ValueError(f"source_start {source_start}s is past the end of {path}")
                dur_us = to_us(duration) if duration is not None else int(available / speed)
                if int(round(dur_us * speed)) > available:
                    raise ValueError(
                        f"Clip needs {dur_us * speed / US:.2f}s of source but {path} has only "
                        f"{available / US:.2f}s after source_start")
                mat_duration = to_us(info.duration)
            else:
                dur_us = to_us(duration)
                mat_duration = src_us + int(round(dur_us * speed))
            src_dur_us = int(round(dur_us * speed))

        start_us = self._place(t, start, dur_us)
        width = info.width or self.width
        height = info.height or self.height
        material = {
            "aigc_type": "none", "audio_fade": None, "category_id": "", "category_name": "local",
            "check_flag": 63487, "crop": {
                "lower_left_x": 0.0, "lower_left_y": 1.0, "lower_right_x": 1.0,
                "lower_right_y": 1.0, "upper_left_x": 0.0, "upper_left_y": 0.0,
                "upper_right_x": 1.0, "upper_right_y": 0.0},
            "crop_ratio": "free", "crop_scale": 1.0, "duration": mat_duration,
            "has_audio": bool(info.has_audio) if kind == "video" else False,
            "height": height, "id": new_id(), "local_material_id": "", "material_id": "",
            "material_name": Path(path).name, "media_path": "", "path": abs_path,
            "type": kind, "width": width,
        }
        self.materials["videos"].append(material)
        helpers = [_speed(speed), _canvas(), _sound_channel()]
        self.materials["speeds"].append(helpers[0])
        self.materials["canvases"].append(helpers[1])
        self.materials["sound_channel_mappings"].append(helpers[2])

        seg = _base_segment(material["id"], start_us, dur_us, src_us, src_dur_us, speed,
                            volume if kind == "video" else 1.0,
                            [h["id"] for h in helpers], t.render_index)
        seg["clip"] = _clip(scale, x, y)
        seg["track_render_index"] = t.render_index
        seg["uniform_scale"]["value"] = scale
        _add_fades(seg, dur_us, fade_in, fade_out)
        if zoom_from is not None or zoom_to is not None:
            z0 = scale if zoom_from is None else float(zoom_from)
            z1 = scale if zoom_to is None else float(zoom_to)
            for prop in ("KFTypeScaleX", "KFTypeScaleY"):
                seg["common_keyframes"].append(_keyframe(prop, [(0, z0), (dur_us, z1)]))
        t.segments.append(seg)
        return _describe(seg, t, Path(path).name)

    # ---- text ------------------------------------------------------------ #

    def add_text(self, text: str, start: float, duration: float, track: str = "text",
                 font_size: float = 8.0, color: str = "#FFFFFF", bold: bool = False,
                 italic: bool = False, underline: bool = False, align: str = "center",
                 x: float = 0.0, y: float = 0.0, stroke_color: str | None = "#000000",
                 stroke_width: float = 0.08, background_color: str | None = None,
                 background_alpha: float = 0.6, max_width: float = 0.82,
                 fade_in: float = 0.0, fade_out: float = 0.0, subtitle: bool = False) -> dict:
        """Add a text overlay. font_size follows CapCut's slider (default 15 in app ≈ 8 here
        for 1080x1920 portrait captions; 5-12 is the useful range)."""
        if not text.strip():
            raise ValueError("text is empty")
        aligns = {"left": 0, "center": 1, "right": 2}
        if align not in aligns:
            raise ValueError(f"align must be one of {list(aligns)}")
        t = self.ensure_track("text", track)
        dur_us = to_us(duration)
        start_us = self._place(t, start, dur_us)

        style: dict[str, Any] = {
            "fill": {"alpha": 1.0, "content": {"render_type": "solid",
                                               "solid": {"alpha": 1.0, "color": hex_to_rgb(color)}}},
            "range": [0, utf16_len(text)], "size": float(font_size),
            "bold": bool(bold), "italic": bool(italic), "underline": bool(underline),
        }
        check_flag = 7
        if stroke_color:
            style["strokes"] = [{"content": {"solid": {"alpha": 1.0, "color": hex_to_rgb(stroke_color)}},
                                 "width": float(stroke_width)}]
            check_flag |= 8
        material: dict[str, Any] = {
            "add_type": 0, "alignment": aligns[align], "background_alpha": 1.0,
            "background_color": "", "background_height": 0.14, "background_horizontal_offset": 0.0,
            "background_round_radius": 0.0, "background_style": 0,
            "background_vertical_offset": 0.0, "background_width": 0.14,
            "bold_width": 0.0, "border_alpha": 1.0, "border_color": "", "border_width": 0.08,
            "check_flag": check_flag,
            "content": json.dumps({"styles": [style], "text": text}, ensure_ascii=False),
            "fixed_height": -1.0, "fixed_width": -1.0, "font_category_id": "",
            "font_category_name": "", "font_id": "", "font_name": "", "font_path": "",
            "font_resource_id": "", "font_size": float(font_size), "font_source_platform": 0,
            "font_team_id": "", "font_title": "none", "font_url": "",
            "force_apply_line_max_width": False, "global_alpha": 1.0, "has_shadow": False,
            "id": new_id(), "initial_scale": 1.0, "is_rich_text": False,
            "italic_degree": 0, "ktv_color": "", "language": "", "layer_weight": 1,
            "letter_spacing": 0.0, "line_feed": 1, "line_max_width": float(max_width),
            "line_spacing": 0.02, "name": "", "original_size": [], "preset_category": "",
            "preset_category_id": "", "preset_has_set_alignment": False, "preset_id": "",
            "preset_index": 0, "preset_name": "", "recognize_task_id": "",
            "recognize_type": 0, "relevance_segment": [], "shadow_alpha": 0.9,
            "shadow_angle": -45.0, "shadow_color": "", "shadow_distance": 5.0,
            "shadow_point": {"x": 0.636, "y": -0.636}, "shadow_smoothing": 0.45,
            "shape_clip_x": False, "shape_clip_y": False, "style_name": "",
            "sub_type": 0, "subtitle_keywords": None, "text_alpha": 1.0, "text_color": color,
            "text_curve": None, "text_preset_resource_id": "", "text_size": 30,
            "text_to_audio_ids": [], "tts_auto_update": False,
            "type": "subtitle" if subtitle else "text", "typesetting": 0,
            "underline": bool(underline), "underline_offset": 0.22, "underline_width": 0.05,
            "use_effect_default_color": True, "words": {"end_time": [], "start_time": [], "text": []},
        }
        if background_color:
            material["background_color"] = background_color
            material["background_alpha"] = float(background_alpha)
            material["background_style"] = 1
            material["check_flag"] |= 16
        if stroke_color:
            material["border_color"] = stroke_color
            material["border_width"] = float(stroke_width)
        self.materials["texts"].append(material)

        anim = {"animations": [], "id": new_id(), "multi_language_current": "none", "type": "sticker_animation"}
        self.materials["material_animations"].append(anim)
        seg = _base_segment(material["id"], start_us, dur_us, 0, None, 1.0, 1.0, [anim["id"]],
                            t.render_index)
        seg["clip"] = _clip(1.0, x, y)
        seg["enable_adjust"] = False
        seg["enable_lut"] = False
        seg["track_render_index"] = t.render_index
        _add_fades(seg, dur_us, fade_in, fade_out)
        t.segments.append(seg)
        return _describe(seg, t, text[:40])

    def add_subtitles(self, srt: str, track: str = "subtitles", offset: float = 0.0,
                      font_size: float = 6.0, color: str = "#FFFFFF", y: float = -0.62,
                      stroke_color: str | None = "#000000", background_color: str | None = None,
                      max_width: float = 0.86) -> list[dict]:
        """Add every cue of an SRT (text or path to a .srt file) as subtitle segments."""
        p = Path(srt).expanduser()
        if len(srt) < 4096 and "\n" not in srt and p.suffix.lower() == ".srt":
            if not p.is_file():
                raise FileNotFoundError(f"SRT file not found: {p}")
            srt = p.read_text(encoding="utf-8-sig")
        cues = parse_srt(srt)
        if not cues:
            raise ValueError("No subtitle cues found in the SRT input")
        out = []
        for c in cues:
            out.append(self.add_text(
                c.text, start=c.start + offset, duration=c.end - c.start, track=track,
                font_size=font_size, color=color, y=y, stroke_color=stroke_color,
                background_color=background_color, max_width=max_width, subtitle=True))
        return out

    # ---- audio ----------------------------------------------------------- #

    def add_audio(self, path: str, start: float = 0.0, duration: float | None = None,
                  source_start: float = 0.0, track: str = "audio", volume: float = 1.0,
                  fade_in: float = 0.0, fade_out: float = 0.0,
                  info: MediaInfo | None = None) -> dict:
        """Add voice-over or music. Video files are accepted (their soundtrack is used)."""
        kind = kind_from_ext(path)
        if kind == "photo":
            raise ValueError("Images cannot go on an audio track")
        info = info or _safe_probe(path, kind)
        if info.duration is None and duration is None:
            raise ValueError(f"Cannot read the length of {path}; pass duration explicitly")
        t = self.ensure_track("audio", track)
        src_us = to_us(source_start)
        if info.duration is not None:
            available = to_us(info.duration) - src_us
            if available <= 0:
                raise ValueError(f"source_start {source_start}s is past the end of {path}")
            dur_us = min(to_us(duration), available) if duration is not None else available
            mat_duration = to_us(info.duration)
        else:
            dur_us = to_us(duration)
            mat_duration = src_us + dur_us
        start_us = self._place(t, start, dur_us)

        material = {
            "app_id": 0, "category_id": "", "category_name": "local", "check_flag": 1,
            "copyright_limit_type": "none", "duration": mat_duration, "effect_id": "",
            "formula_id": "", "id": new_id(), "intensifies_path": "", "is_ai_clone_tone": False,
            "is_text_edit_overdub": False, "is_ugc": False, "local_material_id": new_id(),
            "music_id": new_id(), "name": Path(path).name,
            "path": str(Path(path).expanduser().resolve()), "query": "", "request_id": "",
            "resource_id": "", "search_id": "", "source_from": "", "source_platform": 0,
            "team_id": "", "text_id": "", "tone_category_id": "", "tone_category_name": "",
            "tone_effect_id": "", "tone_effect_name": "", "tone_platform": "", "tone_second_category_id": "",
            "tone_second_category_name": "", "tone_speaker": "", "tone_type": "",
            "type": "extract_music", "video_id": "", "wave_points": [],
        }
        self.materials["audios"].append(material)
        helpers = [_speed(1.0), _sound_channel()]
        self.materials["speeds"].append(helpers[0])
        self.materials["sound_channel_mappings"].append(helpers[1])
        if fade_in > 0 or fade_out > 0:
            fade = _audio_fade(fade_in, fade_out)
            self.materials["audio_fades"].append(fade)
            helpers.append(fade)
        seg = _base_segment(material["id"], start_us, dur_us, src_us, dur_us, 1.0, float(volume),
                            [h["id"] for h in helpers], t.render_index)
        seg["clip"] = None
        seg["hdr_settings"] = None
        seg["uniform_scale"] = None
        seg["enable_adjust"] = False
        seg["enable_lut"] = False
        t.segments.append(seg)
        return _describe(seg, t, Path(path).name)

    # ---- transitions ----------------------------------------------------- #

    def add_transition(self, track: str, after_segment: int, name: str, effect_id: str,
                       resource_id: str, duration: float = 0.5, is_overlap: bool = True,
                       category_id: str = "", category_name: str = "", path: str = "") -> dict:
        """Attach a CapCut library transition between segment `after_segment` and the next one
        (0-based, ordered by time) on a video track.

        CapCut library transitions are downloadable resources: effect_id/resource_id must
        come from a real draft (use inspect_draft on a project where you applied the
        transition by hand). For a resource-free transition use fade_in/fade_out.
        """
        t = self.track(track)
        if t.type != "video":
            raise ValueError("Transitions only apply to video tracks")
        segs = sorted(t.segments, key=lambda s: s["target_timerange"]["start"])
        if not 0 <= after_segment < len(segs) - 1:
            raise ValueError(f"after_segment must be between 0 and {len(segs) - 2}")
        if not effect_id or not resource_id:
            raise ValueError("effect_id and resource_id are required (copy them via inspect_draft)")
        seg = segs[after_segment]
        tr_ids = {m["id"] for m in self.materials["transitions"]}
        if any(r in tr_ids for r in seg["extra_material_refs"]):
            raise ValueError("That segment already has a transition")
        mat = {"category_id": category_id, "category_name": category_name,
               "duration": to_us(duration), "effect_id": effect_id, "id": new_id(),
               "is_overlap": bool(is_overlap), "name": name, "path": path, "platform": "all",
               "request_id": "", "resource_id": resource_id, "type": "transition"}
        self.materials["transitions"].append(mat)
        seg["extra_material_refs"].append(mat["id"])
        return {"transition_id": mat["id"], "track": track, "after_segment": after_segment, "name": name}

    # ---- editing --------------------------------------------------------- #

    def remove_segment(self, segment_id: str) -> None:
        for t in self.tracks:
            for s in list(t.segments):
                if s["id"] == segment_id:
                    t.segments.remove(s)
                    self._gc()
                    return
        raise KeyError(f"No segment with id {segment_id}")

    def _gc(self) -> None:
        used: set[str] = set()
        for t in self.tracks:
            for s in t.segments:
                used.add(s["material_id"])
                used.update(s["extra_material_refs"])
        for k, lst in self.materials.items():
            self.materials[k] = [m for m in lst if m["id"] in used]

    # ---- export ---------------------------------------------------------- #

    @property
    def duration_us(self) -> int:
        return max((t.end_us() for t in self.tracks), default=0)

    def summary(self) -> dict:
        tracks = []
        for t in self.tracks:
            segs = []
            for i, s in enumerate(sorted(t.segments, key=lambda s: s["target_timerange"]["start"])):
                tr = s["target_timerange"]
                segs.append({"index": i, "id": s["id"], "start": tr["start"] / US,
                             "end": (tr["start"] + tr["duration"]) / US,
                             "label": self._label(s)})
            tracks.append({"name": t.name, "type": t.type, "segments": segs})
        return {"draft_id": self.id, "name": self.name, "canvas": [self.width, self.height],
                "fps": self.fps, "duration": self.duration_us / US, "tracks": tracks}

    def _label(self, seg: dict) -> str:
        mid = seg["material_id"]
        for m in self.materials["videos"] + self.materials["audios"]:
            if m["id"] == mid:
                return m.get("material_name") or m.get("name", "")
        for m in self.materials["texts"]:
            if m["id"] == mid:
                return json.loads(m["content"])["text"][:40]
        return ""

    def validate(self) -> list[str]:
        """Return a list of problems (empty = OK). Checks references and timing."""
        problems = []
        all_ids = {m["id"] for lst in self.materials.values() for m in lst}
        if not any(t.segments for t in self.tracks):
            problems.append("Draft has no segments")
        for t in self.tracks:
            spans = []
            for s in t.segments:
                if s["material_id"] not in all_ids:
                    problems.append(f"{t.name}: segment {s['id']} -> missing material")
                for r in s["extra_material_refs"]:
                    if r not in all_ids:
                        problems.append(f"{t.name}: segment {s['id']} -> missing helper {r}")
                tr = s["target_timerange"]
                if tr["duration"] <= 0:
                    problems.append(f"{t.name}: segment {s['id']} has zero length")
                spans.append((tr["start"], tr["start"] + tr["duration"]))
            spans.sort()
            for (a0, a1), (b0, _b1) in zip(spans, spans[1:]):
                if b0 < a1:
                    problems.append(f"{t.name}: overlapping segments at {b0 / US:.3f}s")
        for m in self.materials["videos"] + self.materials["audios"]:
            if not Path(m["path"]).exists():
                problems.append(f"Media file missing: {m['path']}")
        return problems

    def media_paths(self) -> list[str]:
        return [m["path"] for m in self.materials["videos"] + self.materials["audios"]]

    def to_content(self) -> dict:
        now = int(time.time())
        tracks = [t for t in self.tracks if t.segments]
        # CapCut draws video tracks first, then text; keep main video at the bottom.
        tracks.sort(key=lambda t: (TRACK_TYPES.index(t.type) if t.type != "audio" else 1, t.render_index))
        return {
            "canvas_config": {"background": None, "height": self.height, "ratio": "original",
                              "width": self.width},
            "color_space": 0,
            "config": {
                "adjust_max_index": 1, "attachment_info": [], "combination_max_index": 1,
                "export_range": None, "extract_audio_last_index": 1, "lyrics_recognition_id": "",
                "lyrics_sync": True, "lyrics_taskinfo": [], "maintrack_adsorb": True,
                "material_save_mode": 0, "multi_language_current": "none",
                "multi_language_list": [], "multi_language_main": "none",
                "multi_language_mode": "none", "original_sound_last_index": 1,
                "record_audio_last_index": 1, "sticker_max_index": 1,
                "subtitle_keywords_config": None, "subtitle_recognition_id": "",
                "subtitle_sync": True, "subtitle_taskinfo": [], "system_font_list": [],
                "video_mute": False, "zoom_info_params": None},
            "cover": None, "create_time": now, "duration": self.duration_us,
            "extra_info": None, "fps": self.fps, "free_render_index_mode_on": False,
            "group_container": None, "id": self.id, "is_drop_frame_timecode": False,
            "keyframe_graph_list": [], "keyframes": {k: [] for k in KEYFRAME_KINDS},
            "last_modified_platform": copy.deepcopy(DEFAULT_PLATFORM),
            "lyrics_effects": [],
            "materials": copy.deepcopy(self.materials), "mutable_config": None,
            "name": self.name, "new_version": DEFAULT_NEW_VERSION,
            "path": "", "platform": copy.deepcopy(DEFAULT_PLATFORM), "relationships": [],
            "render_index_track_mode_on": True, "retouch_cover": None, "source": "default",
            "static_cover_image_path": "", "time_marks": None,
            "tracks": [t.to_json() for t in tracks], "update_time": now,
            "version": DEFAULT_VERSION,
        }

    def to_meta(self, folder: str, root: str) -> dict:
        now_us = int(time.time() * US)
        return {
            "cloud_package_completed_time": "", "draft_cloud_capcut_purchase_info": "",
            "draft_cloud_last_action_download": False, "draft_cloud_materials": [],
            "draft_cloud_purchase_info": "", "draft_cloud_template_id": "",
            "draft_cloud_tutorial_info": "", "draft_cloud_videocut_purchase_info": "",
            "draft_cover": "", "draft_deeplink_url": "", "draft_enterprise_info": {
                "draft_enterprise_extra": "", "draft_enterprise_id": "",
                "draft_enterprise_name": "", "enterprise_material": []},
            "draft_fold_path": folder, "draft_id": self.id, "draft_is_ai_packaging_used": False,
            "draft_is_ai_shorts": False, "draft_is_ai_translate": False,
            "draft_is_article_video_draft": False, "draft_is_from_deeplink": "false",
            "draft_is_invisible": False,
            "draft_materials": [{"type": k, "value": []} for k in (0, 1, 2, 3, 6, 7, 8)],
            "draft_materials_copied_info": [], "draft_name": self.name, "draft_new_version": "",
            "draft_removable_storage_device": "", "draft_root_path": root,
            "draft_segment_extra_info": [], "draft_timeline_materials_size_": 0,
            "draft_type": "", "tm_draft_cloud_completed": "", "tm_draft_cloud_modified": 0,
            "tm_draft_create": self.created_us, "tm_draft_modified": now_us,
            "tm_draft_removed": 0, "tm_duration": self.duration_us,
        }


def _safe_probe(path: str, kind: str) -> MediaInfo:
    try:
        return probe(path)
    except FileNotFoundError:
        raise
    except Exception:
        return MediaInfo(kind=kind)


def _add_fades(seg: dict, dur_us: int, fade_in: float, fade_out: float) -> None:
    fi, fo = to_us(fade_in), to_us(fade_out)
    if fi < 0 or fo < 0:
        raise ValueError("fade_in/fade_out must be >= 0")
    if fi + fo > dur_us:
        raise ValueError("fade_in + fade_out is longer than the segment")
    if not fi and not fo:
        return
    pts: list[tuple[int, float]] = []
    if fi:
        pts += [(0, 0.0), (fi, 1.0)]
    if fo:
        if not fi:
            pts.append((0, 1.0))
        pts += [(dur_us - fo, 1.0), (dur_us, 0.0)]
    # Merge a duplicate point when fade_in ends exactly where fade_out starts.
    dedup: list[tuple[int, float]] = []
    for p in pts:
        if dedup and dedup[-1][0] == p[0]:
            continue
        dedup.append(p)
    seg["common_keyframes"].append(_keyframe("KFTypeAlpha", dedup))


def _describe(seg: dict, track: Track, label: str) -> dict:
    tr = seg["target_timerange"]
    return {"segment_id": seg["id"], "track": track.name, "start": tr["start"] / US,
            "end": (tr["start"] + tr["duration"]) / US, "label": label}
