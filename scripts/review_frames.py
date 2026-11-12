"""
Extract still frames from a rendered video for content review (marketing agent, /video-review).

  .venv/bin/python scripts/review_frames.py storage/videos/<folder>

Writes storage/review-frames/<folder>/:
  scene_<N>_start.jpg, scene_<N>_mid.jpg   one pair per script segment (first 0.3 s and middle)
  facts.json                                duration, size, codecs, per-scene timing, line/text per scene

The video folder itself is only read, never modified.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

GAP, END_HOLD = 0.25, 0.8   # must match demo.py
FRAME_WIDTH = 540            # half of 1080, enough to read on-screen text


def ffmpeg_bin() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def probe(ff: str, video: Path) -> dict:
    """Parse `ffmpeg -i` output (ffprobe is not bundled with imageio-ffmpeg)."""
    err = subprocess.run([ff, "-hide_banner", "-i", str(video)], capture_output=True, text=True).stderr
    info = {}
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err)
    if m:
        info["duration_s"] = round(int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]), 2)
    m = re.search(r"Video: (\w+).*?, (\d{2,5})x(\d{2,5})", err)
    if m:
        info["video_codec"], info["width"], info["height"] = m[1], int(m[2]), int(m[3])
    m = re.search(r"Audio: (\w+)", err)
    info["audio_codec"] = m[1] if m else None
    info["size_mb"] = round(video.stat().st_size / (1024 * 1024), 1)
    return info


def scene_spans(segments: list) -> list:
    spans, t = [], 0.0
    for i, seg in enumerate(segments):
        dur = seg.get("scene_dur") or (float(seg.get("duration") or 2.0) + GAP
                                       + (END_HOLD if i == len(segments) - 1 else 0))
        spans.append((t, dur))
        t += dur
    return spans


def grab(ff: str, video: Path, at: float, dest: Path) -> None:
    subprocess.run([ff, "-loglevel", "error", "-y", "-ss", f"{at:.2f}", "-i", str(video),
                    "-frames:v", "1", "-vf", f"scale={FRAME_WIDTH}:-2", str(dest)], check=True)


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    folder = Path(sys.argv[1]).resolve()
    video = folder / "video.mp4"
    if not video.is_file():
        sys.exit(f"No video.mp4 in {folder}")
    script = json.loads((folder / "script.json").read_text(encoding="utf-8"))
    segments = script.get("segments") or []

    repo = Path(__file__).resolve().parent.parent
    out = repo / "storage" / "review-frames" / folder.name
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("scene_*.jpg"):
        old.unlink()

    ff = ffmpeg_bin()
    facts = probe(ff, video)
    scenes = []
    for i, (start, dur) in enumerate(scene_spans(segments)):
        seg = segments[i]
        for tag, at in (("start", start + min(0.3, dur / 3)), ("mid", start + dur / 2)):
            grab(ff, video, min(at, max(facts.get("duration_s", at) - 0.1, 0)), out / f"scene_{i + 1}_{tag}.jpg")
        scenes.append({"scene": i + 1, "kind": seg.get("kind"), "speaker": seg.get("speaker"),
                       "start_s": round(start, 2), "dur_s": round(dur, 2),
                       "line": seg.get("line"), "text": seg.get("text")})
    facts["scenes"] = scenes
    facts["hook_end_s"] = scenes[0]["dur_s"] if scenes else None
    (out / "facts.json").write_text(json.dumps(facts, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
