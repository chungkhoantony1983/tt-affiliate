"""Render the same video spec straight to MP4 with ffmpeg (no CapCut needed).

Used as a preview or as a fallback when CapCut cannot open the draft.
"""

from __future__ import annotations

import subprocess
import tempfile
import textwrap
from pathlib import Path
from typing import Any

from .common import (ASPECTS, OUTPUT_DIR, POSITIONS, fetch_media, find_ffmpeg, find_font,
                     is_video, safe_name)
from .prepare import prepare_spec

XFADE = {
    "dissolve": "fade", "fade": "fade", "叠化": "fade", "slide_left": "slideleft", "向左": "slideleft",
    "slide_up": "slideup", "向上": "slideup", "flash_white": "fadewhite", "闪白": "fadewhite",
    "white_flash": "fadewhite", "flash_black": "fadeblack", "闪黑": "fadeblack", "push_in": "zoomin",
    "推近": "zoomin", "pull_out": "fade", "page_turn": "wipeleft", "glitch": "pixelize",
    "move_left": "smoothleft", "左移": "smoothleft", "move_right": "smoothright", "右移": "smoothright",
}


def _run(cmd: list[str]) -> None:
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("ffmpeg lỗi:\n" + p.stderr[-2500:])


def _esc(v: str) -> str:
    return v.replace("\\", "/").replace(":", r"\:").replace("'", r"\'")


def _drawtexts(texts: list[dict[str, Any]], W: int, H: int, tmp: Path, scene_idx: int) -> list[str]:
    filters = []
    for j, t in enumerate(texts):
        font = find_font(bool(t.get("bold", True)))
        if not font:
            raise RuntimeError("Không tìm thấy font TTF hỗ trợ tiếng Việt; đặt 'font_file' trong config.")
        fs = int(float(t["size"]) * 7 * W / 1080)
        per_line = max(8, int(0.8 * W / (fs * 0.6)))
        lines = []
        for para in str(t["text"]).split("\n"):
            lines += textwrap.wrap(para, per_line) or [""]
        lh = int(fs * 1.3)
        y = float(t.get("y", POSITIONS.get(t["position"], -0.68)))
        yc = H / 2 - y * H / 2
        top = yc - lh * len(lines) / 2
        a, b = float(t["start"]), float(t["end"])
        fade = f"if(lt(t\\,{a}+0.3)\\,(t-{a})/0.3\\,1)"
        for k, line in enumerate(lines):
            f = tmp / f"s{scene_idx}_t{j}_l{k}.txt"
            f.write_text(line, "utf-8")
            opts = [
                f"fontfile='{_esc(font)}'", f"textfile='{_esc(str(f))}'", "expansion=none", f"fontsize={fs}",
                f"fontcolor={t['color']}", "x=(w-text_w)/2", f"y={int(top + k * lh)}",
                f"enable='between(t,{a},{b})'", f"alpha='{fade}'",
            ]
            if t.get("bg"):
                opts += ["box=1", f"boxcolor={t['bg']}@{t.get('bg_alpha', 0.9)}", f"boxborderw={int(fs * 0.3)}"]
            if t.get("border"):
                opts += [f"borderw={max(2, int(fs * 0.06))}", f"bordercolor={t['border']}"]
            if t.get("shadow", not t.get("bg")):
                opts += ["shadowx=3", "shadowy=3", "shadowcolor=black@0.6"]
            filters.append("drawtext=" + ":".join(opts))
    return filters


def _scene_clip(sc: dict[str, Any], i: int, W: int, H: int, fps: int, tmp: Path, ff: str) -> Path:
    out = tmp / f"scene_{i:02d}.mp4"
    d = sc["duration"]
    frames = int(round(d * fps))
    base = (f"split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
            f"boxblur=30:2,eq=brightness=-0.12[bg];[b]scale={W}:{H}:force_original_aspect_ratio=decrease[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1")
    if sc.get("media"):
        media = fetch_media(sc["media"])
        if is_video(media):
            inp = ["-ss", str(sc.get("trim_start", 0)), "-t", str(d), "-i", str(media)]
            chain = base + f",fps={fps}"
        else:
            inp = ["-i", str(media)]
            motion = sc["motion"]
            z, x = "1", "iw/2-(iw/zoom/2)"
            if motion == "zoom_in":
                z = f"1+0.15*on/{frames}"
            elif motion == "zoom_out":
                z = f"1.15-0.15*on/{frames}"
            elif motion in ("pan_left", "pan_right"):
                z = "1.15"
                x = f"(iw-iw/zoom)*on/{frames}" if motion == "pan_right" else f"(iw-iw/zoom)*(1-on/{frames})"
            chain = (base + f",scale={W * 2}:{H * 2},zoompan=z='{z}':x='{x}':y='ih/2-(ih/zoom/2)'"
                     f":d={frames}:s={W}x{H}:fps={fps}")
    else:
        inp = ["-f", "lavfi", "-i", f"color=c={sc['background']}:s={W}x{H}:r={fps}:d={d}"]
        chain = "setsar=1"
    chain = ",".join([chain] + _drawtexts(sc["texts"], W, H, tmp, i)) + ",format=yuv420p"
    _run([ff, "-y", *inp, "-filter_complex", chain, "-t", str(d), "-r", str(fps), "-an",
          "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", str(out)])
    return out


def render_mp4(spec: dict[str, Any], output: str | None = None) -> dict[str, Any]:
    spec = prepare_spec(spec)
    # xfade overlaps neighbours; extend each clip by its overlap so the MP4 is as long as the
    # CapCut draft and a voiceover timed to the spec is not cut off.
    last_i = len(spec["scenes"]) - 1
    spec["scenes"] = [dict(sc, duration=sc["duration"] + (0 if i == last_i else
                                                          0.4 if sc.get("transition") else 0.04))
                      for i, sc in enumerate(spec["scenes"])]
    ff = find_ffmpeg()
    if not ff:
        raise RuntimeError("Chưa có ffmpeg. Trên macOS: brew install ffmpeg")
    W, H = ASPECTS[spec["aspect"]]
    fps = int(spec["fps"])
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = Path(output) if output else OUTPUT_DIR / f"{safe_name(spec['name'])}.mp4"
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        clips = [_scene_clip(sc, i, W, H, fps, tmp, ff) for i, sc in enumerate(spec["scenes"])]
        inputs: list[str] = []
        for c in clips:
            inputs += ["-i", str(c)]
        parts, last, offset = [], "[0:v]", 0.0
        starts = [0.0]  # when each scene begins in the final video (for per-scene narration)
        for k in range(1, len(clips)):
            prev = spec["scenes"][k - 1]
            tr = prev.get("transition")
            dur = 0.4 if tr else 0.04
            offset += prev["duration"] - dur
            starts.append(offset)
            label = f"[x{k}]"
            parts.append(f"{last}[{k}:v]xfade=transition={XFADE.get(tr or 'fade', 'fade')}:"
                         f"duration={dur}:offset={offset:.3f}{label}")
            last = label
        total = offset + spec["scenes"][-1]["duration"]
        vgraph = ";".join(parts) if parts else "[0:v]null[x0]"
        vout = last if parts else "[x0]"

        audio_inputs, afilters, amix = [], [], []
        n = len(clips)
        narr = []
        for k, sc in enumerate(spec["scenes"]):
            if sc.get("audio"):
                audio_inputs += ["-i", str(fetch_media(sc["audio"]))]
                ms = int(starts[k] * 1000)
                afilters.append(f"[{n}:a]adelay={ms}|{ms},volume={float(sc.get('audio_volume', 1.0))}[n{k}]")
                narr.append(f"[n{k}]")
                n += 1
        if narr:
            afilters.append("".join(narr) + f"amix=inputs={len(narr)}:duration=longest:normalize=0,"
                            f"atrim=0:{total:.3f}[av0]")
        for key in ("music", "voiceover"):
            a = spec.get(key)
            if not a:
                continue
            if isinstance(a, str):
                a = {"path": a}
            path = fetch_media(a["path"])
            vol = float(a.get("volume", 0.35 if key == "music" else 1.0))
            if key == "music" and narr:
                vol = min(vol, 0.15)  # duck under narration
            if key == "music":
                audio_inputs += ["-stream_loop", "-1", "-i", str(path)]
                afilters.append(f"[{n}:a]atrim=0:{total:.3f},volume={vol},afade=t=in:d=0.5,"
                                f"afade=t=out:st={max(total - 1, 0):.3f}:d=1[am]")
                amix.append("[am]")
            else:
                audio_inputs += ["-i", str(path)]
                afilters.append(f"[{n}:a]atrim=0:{total:.3f},volume={vol}[av]")
                amix.append("[av]")
            n += 1
        graph = vgraph
        maps = ["-map", vout]
        if amix:
            graph += ";" + ";".join(afilters)
            if narr:
                amix.append("[av0]")
            if len(amix) >= 2:
                graph += ";" + "".join(amix) + f"amix=inputs={len(amix)}:duration=first:normalize=0[aout]"
                maps += ["-map", "[aout]"]
            else:
                maps += ["-map", amix[0]]
        _run([ff, "-y", *inputs, *audio_inputs, "-filter_complex", graph, *maps, "-t", f"{total:.3f}",
              "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
              "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(out)])
    return {"mp4_path": str(out), "duration_s": round(total, 2), "size": f"{W}x{H}"}
