"""
Daily no-equipment exercise video (not a sales video).

Every series runs: intro video (curiosity: origin, who it is for, 1–2 sourced highlights, when to
practise) → one video per move → summary video recapping every move in at most 3 minutes.

Next item in content/exercise_curriculum.json → narration from the curriculum text (no LLM, so the
text is exactly what the operator approved) → Gemini TTS → clips with captions → approval →
Google Drive → item marked done.

Clips that show the actual move are made by hand in the Gemini app from prompts this module writes
(storage/clips/<series>/prompts_*.txt). An item without clips stops before any voice call.

  python demo.py --exercise                    # make the next item (or write its clip prompts)
  python demo.py --exercise --allow-stock      # generic Pixabay clips instead (needs PIXABAY_API_KEY)
  python demo.py --exercise-rerender DIR       # re-render a folder (no new TTS calls)

Voice: training content uses the northern male narrator.
"""
import json
import os
import subprocess
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

import demo

CURRICULUM = Path("content/exercise_curriculum.json")
PIXABAY_CACHE = Path("storage/pixabay_cache")   # Pixabay terms: cache search results for 24 h
LOCAL_CLIPS = Path("storage/clips")              # operator's own clips, used before Pixabay
VIDEO_BOX = (360, 920)                           # top y and height of the clip area (texts above/below)
UA = {"User-Agent": "tt-affiliate-video/1.0"}    # Pixabay answers 403 to Python's default UA
# Separate daily quota from the product videos (gemini-3.8-flash-tts). Not the -lite model:
# it read the director's notes aloud (2026-11-12 test).
DEFAULT_TTS_MODEL = "gemini-3.1-flash-tts-preview"
# Intro (6 lines) and summary (10 lines) use yet another model so they never eat the move videos' quota
EXTRA_TTS_MODEL = "gemini-2.5-flash-preview-tts"
SUMMARY_MAX_SECONDS = 180
CLIPS_PER_VIDEO = 3
W, H = demo.W, demo.H


# ---------------------------------------------------------------------------
# Curriculum
# ---------------------------------------------------------------------------

def load_curriculum() -> dict:
    return json.loads(CURRICULUM.read_text(encoding="utf-8"))


def next_move(cur: dict):
    """First move not done yet that has steps written. Returns (series, move) or (None, None)."""
    for series in cur["series"]:
        for move in series["moves"]:
            if not move.get("done") and move.get("steps"):
                return series, move
    return None, None


def next_item(cur: dict):
    """What to make next: ("intro", series, None), ("move", series, move) or ("summary", series, None).

    A series is finished before the next one starts. A series whose intro or moves are not written
    yet blocks (returns ("blocked", series, None)) rather than being skipped."""
    for series in cur["series"]:
        intro, summary = series.get("intro_video"), series.get("summary_video")
        if not intro or not intro.get("segments"):
            if not all(m.get("done") for m in series["moves"]):
                return "blocked", series, None
        elif not intro.get("done"):
            return "intro", series, None
        for move in series["moves"]:
            if not move.get("done"):
                return ("move", series, move) if move.get("steps") else ("blocked", series, None)
        if summary and not summary.get("done"):
            return "summary", series, None
    return None, None, None


def mark_done(series_id: str, item) -> None:
    """item: move number, "intro" or "summary"."""
    cur = load_curriculum()
    for series in cur["series"]:
        if series["id"] != series_id:
            continue
        if item in ("intro", "summary"):
            series[f"{item}_video"]["done"] = True
        for move in series["moves"]:
            if move["n"] == item:
                move["done"] = True
    CURRICULUM.write_text(json.dumps(cur, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _following(cur: dict, series: dict, move: dict):
    """The move after this one (for the 'see you tomorrow' line), or None."""
    moves = series["moves"]
    idx = next(i for i, m in enumerate(moves) if m["n"] == move["n"])
    return moves[idx + 1] if idx + 1 < len(moves) else None


def build_script(cur: dict, series: dict, move: dict) -> dict:
    """Segments straight from the approved curriculum text: intro, one per step, closing."""
    title = f"Bài {move['n']}: {move['name']}"
    segs = [{"kind": "ex_intro", "speaker": "narrator",
             "line": f"{series['title']}, bài {move['n']}: {move['name']}. {series['prepare']}",
             "screen": series["prepare"],  # the title is already at the top of the frame
             "text": "Chuẩn bị"}]
    steps = move["steps"]
    for i, step in enumerate(steps, 1):
        segs.append({"kind": "ex_step", "speaker": "narrator", "line": step, "text": f"Bước {i}/{len(steps)}"})

    nxt = _following(cur, series, move)
    if nxt:
        tomorrow = f"Ngày mai mình tập bài {nxt['n']}, {nxt['name']} nhé."
    elif series.get("summary_video"):
        tomorrow = f"Ngày mai mình tổng kết lại cả {len(series['moves'])} động tác nhé."
    else:
        tomorrow = "Theo dõi để tập chuỗi tiếp theo nhé."
    careful = move.get("careful", "")
    segs.append({"kind": "ex_end", "speaker": "narrator",
                 "line": f"Làm {move['reps'].lower()}. {careful} "
                         f"Đây là bài vận động nhẹ, không phải phương pháp chữa bệnh. {tomorrow}",
                 "text": move["reps"]})
    for s in segs:
        s["line"] = " ".join(s["line"].split())

    caption = (f"{series['title']} – {title}. {series['intro']} "
               f"Lưu lại để tập mỗi sáng. Bài tập vận động nhẹ, không phải phương pháp chữa bệnh.")
    return {"hook": title, "series_id": series["id"], "series_title": series["title"], "item": move["n"],
            "careful": careful, "caption": caption, "hashtags": series.get("hashtags", [])[:5],
            "segments": segs}


def build_intro_script(series: dict) -> dict:
    """Series intro: lines and screen texts as written (and source-checked) in the curriculum."""
    intro = series["intro_video"]
    segs = [{"kind": s["kind"], "speaker": "narrator", "line": " ".join(s["line"].split()),
             "screen": s.get("screen", ""), "text": s["text"], "clip": s.get("clip", "00.mp4")}
            for s in intro["segments"]]
    return {"hook": intro["title"], "series_id": series["id"], "series_title": series["title"],
            "item": "intro", "caption": intro["caption"], "hashtags": series.get("hashtags", [])[:5],
            "segments": segs}


def build_summary_script(series: dict) -> dict:
    """Series summary: opening, one quick line per move (name + cue + reps), closing."""
    summary = series["summary_video"]
    segs = [{"kind": "ex_info", "speaker": "narrator", "line": summary["opening"],
             "screen": f"{len(series['moves'])} động tác · tập liền một mạch", "text": "Tổng kết"}]
    for m in series["moves"]:
        segs.append({"kind": "ex_recap", "speaker": "narrator", "move_n": m["n"],
                     "line": f"Bài {m['n']}, {m['name']}. {m['cue']} {m['reps']}.",
                     "screen": f"{m['cue']} {m['reps']}.", "text": f"Bài {m['n']} · {m['name']}"})
    segs.append({"kind": "ex_info", "speaker": "narrator", "line": summary["closing"],
                 "screen": "Tập đều mỗi sáng · chỉ làm trong sức mình", "text": "Hết bài"})
    for s in segs:
        s["line"] = " ".join(s["line"].split())
    return {"hook": summary["title"], "series_id": series["id"], "series_title": series["title"],
            "item": "summary", "caption": summary["caption"], "hashtags": series.get("hashtags", [])[:5],
            "segments": segs}


# ---------------------------------------------------------------------------
# Pixabay illustration clips
# ---------------------------------------------------------------------------

def _pixabay_search(query: str) -> list:
    PIXABAY_CACHE.mkdir(parents=True, exist_ok=True)
    cache = PIXABAY_CACHE / f"{demo._slug(query)}.json"
    if cache.exists() and time.time() - cache.stat().st_mtime < 24 * 3600:
        return json.loads(cache.read_text(encoding="utf-8"))
    key = os.environ.get("PIXABAY_API_KEY", "").strip()
    if not key:
        raise RuntimeError("PIXABAY_API_KEY not set in .env")
    url = "https://pixabay.com/api/videos/?" + urllib.parse.urlencode(
        {"key": key, "q": query, "per_page": 200, "safesearch": "true"})
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        hits = json.load(r).get("hits", [])
    cache.write_text(json.dumps(hits), encoding="utf-8")
    return hits


def _clip_dir(series: dict) -> Path:
    return LOCAL_CLIPS / series["id"]


def scene_clip_files(series: dict, move: dict):
    """Per-scene clip files that show the actual move, or None if this move has no step clips yet.

    storage/clips/<series>/00.mp4      ready stance, shared by every move (intro + closing scenes)
    storage/clips/<series>/NN_K.mp4    step K of move NN
    A step without its own clip uses the nearest earlier step's clip."""
    d, nn = _clip_dir(series), f"{move['n']:02d}"
    steps = [d / f"{nn}_{k}.mp4" for k in range(1, len(move["steps"]) + 1)]
    if not any(p.exists() for p in steps):
        return None
    resolved, last = [], next(p for p in steps if p.exists())
    for p in steps:
        last = p if p.exists() else last
        resolved.append(last)
    ready = d / "00.mp4"
    calm = ready if ready.exists() else resolved[0]
    return [calm] + resolved + [calm]


# Extra camera angles for steps that are hard to read from the front (move["angles"] = {"K": view}).
# The angle clip plays in a small panel beside the front clip, so the front view stays the main one.
ANGLE_VIEWS = {
    "side": ("Góc nghiêng", "side view from his left, the whole body in profile"),
    "back": ("Nhìn từ sau", "back view from behind him, so left and right match the viewer's"),
}


def _angle_wanted(move: dict) -> list:
    """[(step k, view, file name)] for the angle clips this move asks for."""
    nn = f"{move['n']:02d}"
    return [(int(k), view, f"{nn}_{k}_{view}.mp4") for k, view in sorted(move.get("angles", {}).items())
            if view in ANGLE_VIEWS and 1 <= int(k) <= len(move["steps"])]


def scene_angle_files(series: dict, move: dict) -> list:
    """Per scene (same order as scene_clip_files): (path, view) of an existing angle clip, or None."""
    d = _clip_dir(series)
    by_step = {k: (d / name, view) for k, view, name in _angle_wanted(move) if (d / name).exists()}
    return [None] + [by_step.get(k) for k in range(1, len(move["steps"]) + 1)] + [None]


def attach_angles(script: dict, series: dict, move: dict, out_dir: Path) -> None:
    """Copy the move's angle clips into the video folder; script["scene_angle"][i] = {clip, label} or None."""
    angles = scene_angle_files(series, move)
    script["scene_angle"] = [None] * len(script["segments"])
    for i, a in enumerate(angles[:len(script["segments"])]):
        if not a:
            continue
        path, view = a
        dest = out_dir / f"clip_{len(script['clips'])}.mp4"
        dest.write_bytes(path.read_bytes())
        script["clips"].append({"file": dest.name, "source": f"local:{path.name}"})
        script["scene_angle"][i] = {"clip": len(script["clips"]) - 1, "label": ANGLE_VIEWS[view][0]}


def write_prompts(series: dict, move: dict) -> Path:
    """prompts_NN.txt with one Gemini-app video prompt per clip still missing for this move."""
    d, nn = _clip_dir(series), f"{move['n']:02d}"
    d.mkdir(parents=True, exist_ok=True)
    wanted = []
    if not (d / "00.mp4").exists() and series.get("ready_en"):
        wanted.append(("00.mp4", "Tư thế chuẩn bị (dùng chung cho mọi bài)",
                       f"Over about eight seconds he {series['ready_en']}."))
    for k, (vi, en) in enumerate(zip(move["steps"], move.get("steps_en", [])), 1):
        if not (d / f"{nn}_{k}.mp4").exists():
            wanted.append((f"{nn}_{k}.mp4", f"Bước {k}: {vi}", f"Over about eight seconds he {en}."))
    steps_en = move.get("steps_en", [])
    for k, view, name in _angle_wanted(move):
        if not (d / name).exists() and k <= len(steps_en):
            label, framing = ANGLE_VIEWS[view]
            wanted.append((name, f"Bước {k} – {label} (khung nhỏ cạnh clip chính): {move['steps'][k - 1]}",
                           f"Over about eight seconds he {steps_en[k - 1]}.",
                           MOVE_LOOK.replace("front view", framing)))
    return _write_prompt_file(series, d / f"prompts_{nn}.txt",
                              f"{series['title']} bài {move['n']}: {move['name']}", wanted)


def _first_existing(paths: list):
    return next((p for p in paths if p.exists()), None)


def intro_clip_files(series: dict):
    """Per-scene clips for the intro (each scene names its clip; missing ones fall back to the
    other intro clips or the ready stance). None if no usable clip exists yet."""
    d = _clip_dir(series)
    pool = [d / "00.mp4"] + [d / n for n in series["intro_video"].get("clip_prompts", {})]
    if not _first_existing(pool):
        return None
    return [(d / s.get("clip", "00.mp4")) if (d / s.get("clip", "00.mp4")).exists() else _first_existing(pool)
            for s in series["intro_video"]["segments"]]


def summary_clip_files(series: dict, script: dict):
    """Per-scene clips for the summary: each move shows its key step (peak_step), the opening and
    closing show the ready stance. None if no clip exists at all."""
    d = _clip_dir(series)
    moves = {m["n"]: m for m in series["moves"]}
    files = []
    for seg in script["segments"]:
        m = moves.get(seg.get("move_n"))
        if m:
            nn = f"{m['n']:02d}"
            order = [d / f"{nn}_{m.get('peak_step', 1)}.mp4"] + \
                    [d / f"{nn}_{k}.mp4" for k in range(1, len(m["steps"]) + 1)]
            files.append(_first_existing(order) or _first_existing([d / "00.mp4"]))
        else:
            files.append(_first_existing([d / "00.mp4"]))
    if not any(files):
        return None
    fallback = next(f for f in files if f)
    return [f or fallback for f in files]


def write_intro_prompts(series: dict) -> Path:
    """prompts_intro.txt: the shared ready stance plus the intro's own clips, whichever are missing."""
    d = _clip_dir(series)
    d.mkdir(parents=True, exist_ok=True)
    wanted = []
    if not (d / "00.mp4").exists() and series.get("ready_en"):
        wanted.append(("00.mp4", "Tư thế chuẩn bị (dùng chung cho mọi bài)",
                       f"Over about eight seconds he {series['ready_en']}."))
    segs = series["intro_video"]["segments"]
    for name, action in series["intro_video"].get("clip_prompts", {}).items():
        if not (d / name).exists():
            # Show which narration each clip plays under, so the operator can judge the fit
            used = [f"cảnh {i}: {s.get('screen') or s.get('text', '')}" for i, s in enumerate(segs, 1)
                    if s.get("clip") == name]
            # Intro shots set their own framing (wide, close-up), so no full-body rule
            wanted.append((name, "; ".join(used) or "Cảnh cho video mở đầu", action, CINEMATIC_LOOK))
    return _write_prompt_file(series, d / "prompts_intro.txt",
                              f"{series['title']} — video mở đầu", wanted)


# Avoid the word "tripod": video models tend to draw one in the frame. Describe the framing instead.
MOVE_LOOK = ("Realistic vertical 9:16 video, full body visible from head to feet, front view, locked-off "
             "static shot from chest height with no camera movement, slow smooth tai chi tempo, natural light. "
             "No text, no captions, no music, no other people, no camera equipment or stands visible in the frame.")
CINEMATIC_LOOK = ("Realistic vertical 9:16 video, slow smooth tai chi tempo, natural light. "
                  "No text, no captions, no music, no other people.")


def _write_prompt_file(series: dict, path: Path, heading: str, wanted: list) -> Path:
    """wanted: (file name, Vietnamese description, action sentence[, look]) per missing clip."""
    d = path.parent
    lines = [f"PROMPT VIDEO CHO APP GEMINI — {heading}", "",
             "Cách làm:",
             "1. Mở gemini.google.com (hoặc app Gemini) → Video → chọn khung Dọc (9:16).",
             "2. Dán từng prompt bên dưới, MỖI PROMPT MỘT CUỘC TRÒ CHUYỆN MỚI (chat cũ làm Gemini bám theo clip",
             "   trước và làm sai động tác). Nhân vật giữ giống nhau nhờ phần mô tả người trong prompt.",
             "3. Xem kỹ: tay, chân, hướng nhìn có đúng như dòng tiếng Việt không. Sai thì tạo lại.",
             f"4. Tải video về, đổi tên đúng như dòng 'Lưu thành', bỏ vào thư mục {d}/",
             "5. Đủ clip thì chạy lại: .venv/bin/python demo.py --exercise",
             "   (Hết lượt tạo video trong ngày thì làm trước các clip lẻ 1, 3: clip thiếu sẽ mượn clip khác.)",
             ""]
    for name, vi, action, *look in wanted:
        lines += ["=" * 70, f"Lưu thành: {name}", f"Nội dung: {vi}", "",
                  f"{look[0] if look else MOVE_LOOK} The person is "
                  f"{series.get('character_en', 'a calm middle-aged person')}. {action}", ""]
    if not wanted:
        lines.append("Đã đủ clip.")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def copy_scene_clips(files: list, out_dir: Path) -> tuple:
    """Copy the distinct clips into the video folder. Returns (clips, scene index → clip index)."""
    clips, index = [], {}
    for f in files:
        if f not in index:
            dest = out_dir / f"clip_{len(clips)}.mp4"
            dest.write_bytes(f.read_bytes())
            index[f] = len(clips)
            clips.append({"file": dest.name, "source": f"local:{f.name}"})
    return clips, [index[f] for f in files]


def pick_clips(series: dict, move_n: int) -> list:
    """Relevant real-footage Pixabay clips (required tag present, excluded ids and AI-generated
    dropped), rotated per move."""
    tag = series.get("clip_tag", "").lower()
    exclude = set(series.get("clip_exclude", []))
    hits = [h for h in _pixabay_search(series.get("clip_query", tag))
            if tag in h.get("tags", "").lower() and "ai generated" not in h.get("tags", "").lower()
            and h["id"] not in exclude]
    if not hits:
        raise RuntimeError(f"No Pixabay clips tagged '{tag}'")
    hits.sort(key=lambda h: h["id"])
    start = (move_n - 1) % len(hits)
    return [hits[(start + k) % len(hits)] for k in range(min(CLIPS_PER_VIDEO, len(hits)))]


def download_clips(hits: list, out_dir: Path) -> list:
    clips = []
    for k, h in enumerate(hits):
        v = h["videos"]
        # 'medium' is ~1280–1920 wide: sharp enough for the 1080-wide frame, quick to decode
        src = next((v[s] for s in ("medium", "large", "small") if v.get(s, {}).get("url")), None)
        if not src:
            continue
        dest = out_dir / f"clip_{k}.mp4"
        req = urllib.request.Request(src["url"], headers=UA)
        dest.write_bytes(demo._http_bytes(req, timeout=180))
        clips.append({"file": dest.name, "source": f"pixabay:{h['id']}", "page": h["pageURL"]})
    if not clips:
        raise RuntimeError("Could not download any Pixabay clip")
    return clips


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

def _overlay(script: dict, i: int, angle_box: tuple = None):
    """Transparent 1080x1920 layer with the texts for scene i (kept clear of TikTok's bottom UI).
    angle_box: (x, y, w, h) of the angle panel, labelled above it."""
    from PIL import Image, ImageDraw
    seg = script["segments"][i]
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    if angle_box:
        label = (script.get("scene_angle") or [])[i]["label"]
        x, y, w, _ = angle_box
        font = demo._font(30)
        tw = draw.textlength(label, font=font)
        draw.text((x + (w - tw) / 2, y - 44), label, font=font, fill="#FFE14D",
                  stroke_width=4, stroke_fill="black")
    demo._text_block(draw, script["series_title"].upper(), 120, demo._font(40), color="#FFE14D", stroke=4)
    demo._text_block(draw, script["hook"], 180, demo._font(70), stroke=7)
    if script.get("stock", True):  # generic stock footage, not the move itself
        demo._text_block(draw, "Hình minh hoạ", 300, demo._font(30, bold=False), color="#DDDDDD", stroke=3)

    if seg["kind"] == "ex_end":
        y = demo._pill(draw, seg["text"], 1330, demo._font(60), fill="#FFE14D", color="black") + 30
        if script.get("careful"):
            y = demo._text_block(draw, script["careful"], y, demo._font(46), stroke=5, gap=10) + 20
        demo._text_block(draw, "Bài vận động nhẹ, không phải phương pháp chữa bệnh",
                         y, demo._font(34, bold=False), color="#DDDDDD", stroke=4)
    else:
        y = demo._pill(draw, seg["text"], 1310, demo._font(52), fill="#FFE14D", color="black") + 26
        demo._text_block(draw, seg.get("screen", seg["line"]), y, demo._font(50), stroke=5, gap=10)
    return canvas


def _clip_info(path: Path) -> tuple:
    """(width, height, seconds) of a clip, read from ffmpeg's stream info."""
    import re
    err = subprocess.run([demo._ffmpeg_bin(), "-i", str(path)], capture_output=True, text=True).stderr
    m = re.search(r"Video:.*?(\d{3,5})x(\d{3,5})", err)
    d = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err)
    secs = int(d.group(1)) * 3600 + int(d.group(2)) * 60 + float(d.group(3)) if d else 0.0
    return (int(m.group(1)), int(m.group(2))) + (secs,) if m else (1920, 1080, secs)


MAX_SLOWDOWN = 1.6  # a clip shorter than its scene plays up to this much slower before it loops


def _fg_filter(path: Path) -> str:
    """Landscape clips fill the clip box (sides cropped) so people are big enough to see;
    portrait clips are fitted whole so heads and feet stay in frame."""
    bw, bh = W, VIDEO_BOX[1]
    w, h, _ = _clip_info(path)
    if w >= h:
        return f"scale={bw}:{bh}:force_original_aspect_ratio=increase,crop={bw}:{bh}"
    return f"scale={bw}:{bh}:force_original_aspect_ratio=decrease"


def _pingpong(clip: Path) -> Path:
    """clip played forward then backward: loops without the jump back to the first frame
    (slow tai chi motion reads naturally in reverse). Cached next to the clip."""
    pp = clip.with_name(f"_pp_{clip.name}")
    if not pp.exists():
        subprocess.run([demo._ffmpeg_bin(), "-y", "-v", "error", "-i", str(clip), "-filter_complex",
                        "[0:v]split[f][b];[b]reverse[r];[f][r]concat=n=2:v=1:a=0[v]", "-map", "[v]",
                        "-an", "-c:v", "libx264", "-crf", "16", "-preset", "fast", str(pp)], check=True)
    return pp


def _clip_input(clip: Path, dur: float) -> tuple:
    """ffmpeg input args for a scene of dur seconds and the slowdown factor. Short clips (Gemini makes
    8–10 s) are slowed a little to fit the narration; if still too short they ping-pong instead of
    jumping back to the start."""
    clip_secs = _clip_info(clip)[2] or dur
    slow = min(max(dur / clip_secs, 1.0), MAX_SLOWDOWN)
    src = _pingpong(clip) if dur / slow > clip_secs + 0.05 else clip
    return ["-stream_loop", "-1", "-t", f"{dur / slow + 0.1:.3f}", "-i", str(src)], slow


ANGLE_PANEL_W, ANGLE_PANEL_MARGIN = 250, 14  # angle clip panel, right of the (portrait) front clip


def _angle_panel_box(clip: Path) -> tuple:
    """(x, y, w, h) of the angle panel: bottom-right of the clip box."""
    w, h, _ = _clip_info(clip)
    ph = round(ANGLE_PANEL_W * h / w / 2) * 2
    top, box_h = VIDEO_BOX
    return W - ANGLE_PANEL_W - ANGLE_PANEL_MARGIN, top + box_h - ph, ANGLE_PANEL_W, ph


def render(script: dict, out_dir: Path) -> str:
    segs, clips = script["segments"], script["clips"]
    n = len(segs)
    angles = script.get("scene_angle") or [None] * n
    inputs, filters, temp = [], [], []
    for p in out_dir.glob("_pp_*.mp4"):  # left over from a failed render; the clip may have changed
        p.unlink()
    k = 0  # next ffmpeg input index
    for i, seg in enumerate(segs):
        dur = seg["duration"] + demo.GAP + (demo.END_HOLD if i == n - 1 else 0)
        seg["scene_dur"] = dur
        ci = script["scene_clip"][i] if script.get("scene_clip") else i % len(clips)
        clip = out_dir / clips[ci]["file"]
        angle = angles[i] if i < len(angles) else None
        aclip = out_dir / clips[angle["clip"]]["file"] if angle else None
        png = out_dir / f"_scene_{i}.png"
        _overlay(script, i, _angle_panel_box(aclip) if aclip else None).save(png)
        temp.append(png)
        args, slow = _clip_input(clip, dur)
        inputs += args
        v = k
        k += 1
        # Blurred full-frame copy behind, clip in the box between the texts, texts on top
        top, box_h = VIDEO_BOX
        chain = (f"[{v}:v]setpts={slow:.3f}*PTS,fps={demo.FPS},split=2[bgs{i}][fgs{i}];"
                 f"[bgs{i}]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                 f"boxblur=25:2,eq=brightness=-0.18[bg{i}];"
                 f"[fgs{i}]{_fg_filter(clip)}[fg{i}];"
                 f"[bg{i}][fg{i}]overlay=(W-w)/2:{top}+({box_h}-h)/2[base{i}];")
        if aclip:
            aargs, aslow = _clip_input(aclip, dur)
            inputs += aargs
            x, y, pw, ph = _angle_panel_box(aclip)
            chain += (f"[{k}:v]setpts={aslow:.3f}*PTS,fps={demo.FPS},scale={pw - 8}:{ph - 8},"
                      f"pad={pw}:{ph}:4:4:white[ang{i}];"
                      f"[base{i}][ang{i}]overlay={x}:{y}[based{i}];")
            k += 1
            base_label = f"based{i}"
        else:
            base_label = f"base{i}"
        inputs += ["-loop", "1", "-framerate", str(demo.FPS), "-t", f"{dur:.3f}", "-i", str(png)]
        o = k
        k += 1
        filters.append(chain + f"[{base_label}][{o}:v]overlay=0:0,setsar=1,format=yuv420p,"
                               f"trim=duration={dur:.3f}[v{i}]")
        print(f"   Scene {i + 1} [{seg['kind']}]: {dur:.1f}s  {clips[ci]['source']}"
              + (f" (x{slow:.2f} slower)" if slow > 1.01 else "")
              + (f" + {angle['label']}: {clips[angle['clip']]['source']}" if angle else ""))
    base = k
    for i, seg in enumerate(segs):
        inputs += ["-i", str(out_dir / Path(seg["audio_path"]).name)]
        pad = demo.GAP + (demo.END_HOLD if i == n - 1 else 0)
        fade_out_at = max(seg["duration"] - 0.03, 0)
        filters.append(f"[{base + i}:a]aresample=44100,aformat=channel_layouts=mono,"
                       f"afade=t=in:st=0:d=0.015,afade=t=out:st={fade_out_at:.3f}:d=0.03,"
                       f"apad=pad_dur={pad}[a{i}]")
    filters.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[vout]")
    filters.append("".join(f"[a{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1[aout]")

    video_path = out_dir / "video.mp4"
    cmd = [demo._ffmpeg_bin(), "-y", *inputs, "-filter_complex", ";".join(filters),
           "-map", "[vout]", "-map", "[aout]", "-c:v", "libx264", "-preset", "medium", "-crf", "21",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(video_path)]
    print(f"🎬 Rendering exercise video ({n} scenes, {len(clips)} clip(s))...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    for p in temp + list(out_dir.glob("_pp_*.mp4")):  # ping-pong copies are rebuilt on each render
        p.unlink(missing_ok=True)
    if result.returncode != 0:
        print(result.stderr[-3000:])
        raise RuntimeError(f"FFmpeg failed with exit code {result.returncode}")
    size = video_path.stat().st_size / 1e6
    print(f"✅ Video: {video_path}  ({size:.1f} MB, {sum(s['scene_dur'] for s in segs):.1f}s)")
    return str(video_path)


# ---------------------------------------------------------------------------
# Flow
# ---------------------------------------------------------------------------

def write_post_kit(out_dir: Path, script: dict) -> None:
    caption = f"{script['caption']} {' '.join(script['hashtags'])}".strip()
    credits = "\n".join(f"- {c.get('page', c['source'])}" for c in script["clips"])
    (out_dir / "post.txt").write_text(
        "=== CAPTION (copy) ===\n"
        f"{caption}\n\n"
        "=== CHECKLIST ĐĂNG ===\n"
        "[ ] Lấy video.mp4 về điện thoại (app Google Drive)\n"
        "[ ] TikTok → + → Tải lên → chọn video, dán caption\n"
        "[ ] KHÔNG gắn sản phẩm (video bài tập, không phải video bán hàng)\n"
        "[ ] Cài đặt khác → BẬT nhãn 'Nội dung do AI tạo' (giọng đọc AI)\n"
        "[ ] Đăng\n\n"
        "=== CLIP MINH HOẠ (Pixabay không bắt buộc ghi nguồn) ===\n"
        f"{credits}\n",
        encoding="utf-8")


def _item_label(script: dict) -> str:
    return {"intro": "video mở đầu", "summary": "video tổng kết"}.get(script["item"], f"bài {script['item']}")


def finish(out_dir: Path, script: dict, skip_approval: bool) -> dict:
    video_path = render(script, out_dir)
    total = sum(s["scene_dur"] for s in script["segments"])
    if script["item"] == "summary" and total > SUMMARY_MAX_SECONDS:
        print(f"⚠️  Summary is {total:.0f}s, over the {SUMMARY_MAX_SECONDS}s limit — shorten the cues")
    (out_dir / "script.json").write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")
    if not skip_approval and not demo.approval_step(script, video_path):
        print("❌ Rejected — files kept. Re-render without new voice calls: "
              f"python demo.py --exercise-rerender {out_dir}")
        return {"status": "rejected", "dir": str(out_dir)}
    write_post_kit(out_dir, script)
    mark_done(script["series_id"], script["item"])
    print(f"📚 Curriculum: {script['series_title']} {_item_label(script)} → done")
    result = {"status": "ready_for_manual_upload", "dir": str(out_dir)}
    if os.environ.get("DRIVE_FOLDER_ID"):
        result.update(demo.move_to_drive(out_dir, f"Bài tập - {script['series_title']}"))
    return result


def run_next(base_dir: Path, skip_approval: bool, allow_stock: bool = False) -> dict:
    cur = load_curriculum()
    kind, series, move = next_item(cur)
    if kind is None:
        raise RuntimeError(f"Every series in {CURRICULUM} is done — add the next series")
    if kind == "blocked":
        raise RuntimeError(f"Series '{series['title']}' is not written yet (intro_video, steps of every move, "
                           f"summary_video) — fill it in {CURRICULUM} and have it approved")

    if kind == "intro":
        script, files, slug = build_intro_script(series), intro_clip_files(series), "00_gioithieu"
        prompts_fn = lambda: write_intro_prompts(series)
        heading = f"{series['title']} — video mở đầu"
    elif kind == "summary":
        script = build_summary_script(series)
        files, slug = summary_clip_files(series, script), "99_tongket"
        prompts_fn, heading = None, f"{series['title']} — video tổng kết"
    else:
        script, files, slug = build_script(cur, series, move), scene_clip_files(series, move), f"{move['n']:02d}"
        prompts_fn = lambda: write_prompts(series, move)
        heading = f"{series['title']} — bài {move['n']}: {move['name']}"

    if files is None and not allow_stock:
        # Stop before any voice call: the clips have to be made in the Gemini app first
        if not prompts_fn:
            raise RuntimeError("No clips at all for the summary — the move clips are missing from storage/clips")
        prompts = prompts_fn()
        print(f"🎞️  {heading}: chưa có clip. Làm clip theo {prompts}")
        return {"status": "needs_clips", "dir": str(prompts)}
    if files is not None and prompts_fn:
        prompts_fn()  # keeps the list of clips still missing up to date

    out_dir = base_dir / f"{datetime.now():%Y%m%d_%H%M%S}_baitap_{series['id']}_{slug}"
    out_dir.mkdir(parents=True, exist_ok=True)
    print("\n" + "=" * 60)
    print(f"🧘 {heading}")
    print("=" * 60)

    if files is not None:
        script["clips"], script["scene_clip"] = copy_scene_clips(files, out_dir)
        script["stock"] = False
        if kind == "move":
            attach_angles(script, series, move, out_dir)
    else:
        script["clips"] = download_clips(pick_clips(series, move["n"] if move else 1), out_dir)
        script["stock"] = True
    persona = demo.choose_persona({"category": "tập luyện"})
    model = (os.environ.get("EXERCISE_TTS_MODEL", DEFAULT_TTS_MODEL) if kind == "move"
             else os.environ.get("EXERCISE_EXTRA_TTS_MODEL", EXTRA_TTS_MODEL))
    demo.generate_voiceovers(script["segments"], out_dir, persona, model=model)
    script["voice_persona"] = persona
    return finish(out_dir, script, skip_approval)


def rerender(out_dir: Path, skip_approval: bool) -> dict:
    """Re-render with the existing voice. Picks up clips added to storage/clips/ since the first run,
    so a video made with stand-in clips can get the real ones without new voice calls."""
    script = json.loads((out_dir / "script.json").read_text(encoding="utf-8"))
    cur = load_curriculum()
    series = next((s for s in cur["series"] if s["id"] == script["series_id"]), None)
    if series:
        item = script["item"]
        if item == "intro":
            files = intro_clip_files(series)
        elif item == "summary":
            files = summary_clip_files(series, script)
        else:
            move = next(m for m in series["moves"] if m["n"] == item)
            files = scene_clip_files(series, move)
        if files is not None:
            for old in out_dir.glob("clip_*.mp4"):
                old.unlink()
            script["clips"], script["scene_clip"] = copy_scene_clips(files, out_dir)
            script["stock"] = False
            script.pop("scene_angle", None)
            if item not in ("intro", "summary"):
                attach_angles(script, series, move, out_dir)
            print(f"🎞️  Clips: {[c['source'] for c in script['clips']]}")
    return finish(out_dir, script, skip_approval)
