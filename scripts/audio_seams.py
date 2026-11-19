"""
Look for the short noise burst at scene changes (DR-0004, skill audio-check step 2). Local, $0.

  PY=$(git rev-parse --path-format=absolute --git-common-dir)/../.venv/bin/python
  $PY scripts/audio_seams.py storage/videos/<folder>                       # seams of video.mp4
  $PY scripts/audio_seams.py storage/videos/<folder> --audio-files         # each audio_N.mp3 on its own
  $PY scripts/audio_seams.py storage/videos/<folder> --audio-files --scenes 1,3

Video mode (default): decodes the audio track of video.mp4 to mono 16-bit PCM (ffmpeg from
imageio_ffmpeg, 24 kHz like Gemini TTS). Scene times come from script.json, the same way the
renderers lay them out:
  - product video (demo.render_video): scene = length of decoded audio_N.mp3 (falls back to
    segment "duration") + GAP, last scene + END_HOLD; speech ends at the end of the clip.
  - exercise video (exercise.render): scene = "scene_dur"; speech ends at speech_trim[1]-speech_trim[0].
For every scene the window runs from 400 ms before the end of speech to the end of the scene
(GAP, plus END_HOLD on the last one), in 20 ms RMS windows. Scanning that window backwards with the
thresholds of demo._trim_gemini_edges: skip quiet windows (<= -35 dB), then a loud run (> -30 dB) of
at most 8 windows, then a window below -45 dB before it  -> "Nghi tiếng nổ". A real last syllable
fades out through -30..-45 dB, so it does not match; the Gemini burst is abrupt (2026-11-13: ~40 ms
at about -6 dB, ~20 ms of quiet before the clip end).

--audio-files: measures each audio_N.mp3 itself (Dev, after changing the trim/concat code): the same
tail rule over the last 400 ms and the head rule over the first 200 ms (max 5 windows), and the
real demo._trim_gemini_edges is run on the clip to report how many ms it would still cut.

Writes <out-dir>/seams.json and prints a table. Default out-dir: storage/review-frames/<folder>/ of
this checkout (next to review_frames.py output) when the folder is <repo>/storage/videos/<folder>;
storage/review-frames/<folder>__sandbox/ for a copy elsewhere (e.g. sandbox_render.py --keep), with
"sandbox": true in the JSON. The video folder is only read, and an --out-dir inside it or inside any
storage/videos/ is refused (C-0004-5). The result is a signal for a human listener, never a
pass/fail of the audio by itself (C-0004-3).

Exit codes: 0 = measured (flags are in the output), 1 = error (missing file, ffmpeg failure, bad
--out-dir, bad args).
"""
import argparse
import json
import math
import subprocess
import sys
from array import array
from pathlib import Path

CODE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CODE_ROOT))
import demo  # noqa: E402  (GAP, END_HOLD, GEMINI_TTS_RATE, _trim_gemini_edges: one source of truth)

RATE = demo.GEMINI_TTS_RATE          # 24 kHz
WIN = RATE // 50                     # 20 ms, as in _trim_gemini_edges
QUIET_DB, LOUD_DB, DEEP_DB = -35, -30, -45   # thresholds of _trim_gemini_edges
TAIL_MAX_WINDOWS, HEAD_MAX_WINDOWS = 8, 5    # burst length limits of _trim_gemini_edges
TAIL_SPAN, HEAD_SPAN = 20, 10                # windows scanned: last 400 ms / first 200 ms
FLAG, OK = "Nghi tiếng nổ", "OK"


def ffmpeg_bin() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def decode(path: Path) -> array:
    proc = subprocess.run([ffmpeg_bin(), "-v", "error", "-i", str(path), "-vn", "-f", "s16le", "-ac", "1",
                           "-ar", str(RATE), "-"], capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg could not decode {path.name}: {proc.stderr.decode(errors='replace')[-300:]}")
    return array("h", proc.stdout)


def levels(samples: array) -> list:
    """dB of each full 20 ms window (same formula as _trim_gemini_edges)."""
    out = []
    for k in range(len(samples) // WIN):
        chunk = samples[k * WIN:(k + 1) * WIN]
        rms = math.sqrt(sum(x * x for x in chunk) / len(chunk))
        out.append(20 * math.log10(rms / 32768) if rms > 0 else -120.0)
    return out


def find_burst(lv: list, order: list, max_len: int):
    """Mirror of the burst() rule inside demo._trim_gemini_edges: walk `order` (window indexes, edge
    first), skip quiet, take a loud run of 1..max_len windows that is followed by a deep-quiet window.
    Returns (first, last) window index of the run in `order`, or None."""
    j = 0
    while j < len(order) and lv[order[j]] <= QUIET_DB:
        j += 1
    run = j
    while j < len(order) and lv[order[j]] > LOUD_DB:
        j += 1
    if run < j <= run + max_len and j < len(order) and lv[order[j]] < DEEP_DB:
        return order[run], order[j - 1]
    return None


# ---------------------------------------------------------------------------
# Output folder (C-0004-5: never write into a video folder or any storage/videos/)
# ---------------------------------------------------------------------------

def _repo_roots() -> list:
    """This checkout and the main repo (git common dir), whose storage/videos/ hold the real videos."""
    roots = [CODE_ROOT]
    try:
        common = subprocess.run(["git", "-C", str(CODE_ROOT), "rev-parse", "--path-format=absolute",
                                 "--git-common-dir"], capture_output=True, text=True, timeout=10).stdout.strip()
        if common and Path(common).parent.resolve() not in roots:
            roots.append(Path(common).parent.resolve())
    except (OSError, subprocess.SubprocessError):
        pass
    return roots


def is_real_folder(folder: Path) -> bool:
    """True when folder is <repo>/storage/videos/<name> of this checkout or the main repo; False for a
    copy anywhere else (e.g. the temp dir of sandbox_render.py --keep)."""
    return folder.parent in [(r / "storage" / "videos").resolve() for r in _repo_roots()]


def _in_videos_tree(path: Path) -> bool:
    parts = path.parts
    return any(parts[k] == "storage" and parts[k + 1] == "videos" for k in range(len(parts) - 1))


def output_dir(folder: Path, out_dir_arg) -> tuple:
    """(out_dir, sandbox). Default storage/review-frames/<name>/ of this checkout for a real folder,
    storage/review-frames/<name>__sandbox/ for a copy, so the result of a copy never overwrites (or
    is read as) the result of the real video. --out-dir inside the video folder or inside any
    storage/videos/ is refused."""
    sandbox = not is_real_folder(folder)
    if out_dir_arg:
        out = Path(out_dir_arg).expanduser().resolve()
        if out == folder or folder in out.parents or _in_videos_tree(out):
            raise ValueError(f"--out-dir {out} is inside the video folder or a storage/videos/ tree; "
                        f"results must not be written next to videos (C-0004-5)")
        return out, sandbox
    name = folder.name + ("__sandbox" if sandbox else "")
    return CODE_ROOT / "storage" / "review-frames" / name, sandbox


def parse_scenes(text: str, n: int) -> list:
    """'1,3' -> [0, 2] (scene numbers are 1-based like the Studio)."""
    if not text:
        return list(range(n))
    picked = []
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        if not part.isdigit() or not 1 <= int(part) <= n:
            raise ValueError(f"--scenes: '{part}' is not a scene number 1..{n}")
        picked.append(int(part) - 1)
    return sorted(set(picked))


def scene_layout(folder: Path, segments: list) -> list:
    """[(start_s, speech_s, scene_s)] in the order the renderers concatenate the audio."""
    out, t, n = [], 0.0, len(segments)
    for i, seg in enumerate(segments):
        hold = demo.GAP + (demo.END_HOLD if i == n - 1 else 0)
        if seg.get("scene_dur"):                       # exercise.render
            scene = float(seg["scene_dur"])
            trim = seg.get("speech_trim")
            speech = float(trim[1]) - float(trim[0]) if trim else max(scene - hold, 0.0)
        else:                                          # demo.render_video
            audio = folder / f"audio_{i}.mp3"
            speech = len(decode(audio)) / RATE if audio.is_file() else float(seg.get("duration") or 0)
            scene = speech + hold
        out.append((t, speech, scene))
        t += scene
    return out


def check_video(folder: Path, segments: list, picked: list) -> list:
    video = folder / "video.mp4"
    if not video.is_file():
        raise RuntimeError(f"No video.mp4 in {folder}")
    lv = levels(decode(video))
    rows = []
    for i, (start, speech, scene) in enumerate(scene_layout(folder, segments)):
        if i not in picked:
            continue
        speech_end = start + speech
        a = max(int((speech_end - 0.4) * 50), 0)
        b = min(int((start + scene) * 50), len(lv))       # window index range [a, b)
        span = list(range(b - 1, a - 1, -1))              # backwards from the end of the scene
        hit = find_burst(lv, span, TAIL_MAX_WINDOWS)
        gap = lv[int(speech_end * 50):b] or [-120.0]
        tail = lv[a:b] or [-120.0]
        row = {"scene": i + 1, "seam_s": round(start + scene, 3), "speech_end_s": round(speech_end, 3),
               "tail_max_db": round(max(tail), 1), "gap_max_db": round(max(gap), 1), "burst": None,
               "last": i == len(segments) - 1, "result": OK}
        if hit:
            last, first = hit                              # order is backwards
            row["burst"] = {"start_s": round(first / 50, 3), "dur_ms": (last - first + 1) * 20,
                            "peak_db": round(max(lv[first:last + 1]), 1)}
            row["result"] = FLAG
        rows.append(row)
    return rows


def check_files(folder: Path, segments: list, picked: list) -> list:
    rows = []
    for i in picked:
        path = folder / f"audio_{i}.mp3"
        if not path.is_file():
            raise RuntimeError(f"No {path.name} in {folder}")
        samples = decode(path)
        lv = levels(samples)
        n = len(lv)
        tail = find_burst(lv, list(range(n - 1, max(n - TAIL_SPAN, 0) - 1, -1)), TAIL_MAX_WINDOWS)
        head = find_burst(lv, list(range(min(HEAD_SPAN, n))), HEAD_MAX_WINDOWS)
        # _trim_gemini_edges always drops the last partial 20 ms window; only count real cuts
        kept = len(array("h", demo._trim_gemini_edges(samples.tobytes())))
        would_cut = max(n * WIN - kept, 0) / RATE
        row = {"scene": i + 1, "file": path.name, "duration_s": round(len(samples) / RATE, 3),
               "tail_max_db": round(max(lv[-TAIL_SPAN:] or [-120.0]), 1),
               "head_burst": None, "tail_burst": None, "trim_would_cut_ms": round(would_cut * 1000),
               "result": OK}
        for key, hit, backwards in (("head_burst", head, False), ("tail_burst", tail, True)):
            if hit:
                first, last = (hit[1], hit[0]) if backwards else hit
                row[key] = {"start_s": round(first / 50, 3), "dur_ms": (last - first + 1) * 20,
                            "peak_db": round(max(lv[first:last + 1]), 1)}
                row["result"] = FLAG
        rows.append(row)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Flag short noise bursts at scene changes (video.mp4) or at the edges of audio_N.mp3. "
                    "Writes seams.json; only reads the video folder.")
    ap.add_argument("folder", help="video folder, e.g. storage/videos/<folder>")
    ap.add_argument("--audio-files", action="store_true",
                    help="measure each audio_N.mp3 on its own instead of the seams of video.mp4")
    ap.add_argument("--scenes", default="", help="only these scenes, 1-based, comma-separated (e.g. 1,3)")
    ap.add_argument("--out-dir", help="where to write seams.json (default storage/review-frames/<folder>/, "
                                      "or <folder>__sandbox/ for a copy outside storage/videos/; never inside "
                                      "a storage/videos/ tree)")
    args = ap.parse_args()

    folder = Path(args.folder).expanduser().resolve()
    try:
        out_dir, sandbox = output_dir(folder, args.out_dir)
        if not (folder / "script.json").is_file():
            raise RuntimeError(f"No script.json in {folder}")
        segments = json.loads((folder / "script.json").read_text(encoding="utf-8")).get("segments") or []
        if not segments:
            raise RuntimeError("script.json has no segments")
        picked = parse_scenes(args.scenes, len(segments))
        mode = "audio_files" if args.audio_files else "video"
        rows = check_files(folder, segments, picked) if args.audio_files else check_video(folder, segments, picked)
    except (RuntimeError, ValueError, json.JSONDecodeError) as e:
        print(f"audio_seams: error: {e}", file=sys.stderr)
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)
    flagged = [r["scene"] for r in rows if r["result"] != OK]
    report = {"folder": str(folder), "sandbox": sandbox, "source": "copy" if sandbox else "storage/videos",
              "mode": mode, "window_ms": 20,
              "thresholds_db": {"quiet": QUIET_DB, "loud": LOUD_DB, "deep_quiet": DEEP_DB},
              "max_burst_windows": TAIL_MAX_WINDOWS, "gap_s": demo.GAP, "end_hold_s": demo.END_HOLD,
              "flagged_scenes": flagged, "rows": rows,
              "note": "Signal only (C-0004-3): flagged scenes need a human listen."}
    dest = out_dir / "seams.json"
    dest.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.audio_files:
        print(f"{'scene':>5}  {'file':<12} {'dur_s':>6} {'tail_max_db':>11} {'trim_cut_ms':>11}  result")
        for r in rows:
            where = " ".join(f"{k.split('_')[0]}@{r[k]['start_s']}s/{r[k]['peak_db']}dB"
                             for k in ("head_burst", "tail_burst") if r[k])
            print(f"{r['scene']:>5}  {r['file']:<12} {r['duration_s']:>6.2f} {r['tail_max_db']:>11.1f} "
                  f"{r['trim_would_cut_ms']:>11}  {r['result']}{'  ' + where if where else ''}")
    else:
        print(f"{'scene':>5}  {'seam_s':>7} {'tail_max_db':>11} {'gap_max_db':>10}  result")
        for r in rows:
            b = r["burst"]
            extra = f"  burst @{b['start_s']}s {b['dur_ms']} ms {b['peak_db']} dB" if b else ""
            print(f"{r['scene']:>5}  {r['seam_s']:>7.2f} {r['tail_max_db']:>11.1f} {r['gap_max_db']:>10.1f}  "
                  f"{r['result']}{' (end of video)' if r.get('last') else ''}{extra}")
    print(f"{len(flagged)} flagged of {len(rows)} -> {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
