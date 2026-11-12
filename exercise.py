"""
Daily no-equipment exercise video (not a sales video).

Next move in content/exercise_curriculum.json → narration from the curriculum text (no LLM, so the
steps are exactly what the operator approved) → Gemini TTS → one clip per step with step captions
→ approval → Google Drive → move marked done.

Clips that show the actual move are made by hand in the Gemini app from prompts this module writes
(storage/clips/<series>/prompts_NN.txt). A move without clips stops before any voice call.

  python demo.py --exercise                    # make the next move (or write its clip prompts)
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


def mark_done(series_id: str, n: int) -> None:
    cur = load_curriculum()
    for series in cur["series"]:
        if series["id"] == series_id:
            for move in series["moves"]:
                if move["n"] == n:
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
    tomorrow = f"Ngày mai mình tập bài {nxt['n']}, {nxt['name']} nhé." if nxt else "Theo dõi để tập bài tiếp theo nhé."
    careful = move.get("careful", "")
    segs.append({"kind": "ex_end", "speaker": "narrator",
                 "line": f"Làm {move['reps'].lower()}. {careful} "
                         f"Đây là bài vận động nhẹ, không phải phương pháp chữa bệnh. {tomorrow}",
                 "text": move["reps"]})
    for s in segs:
        s["line"] = " ".join(s["line"].split())

    caption = (f"{series['title']} – {title}. {series['intro']} "
               f"Lưu lại để tập mỗi sáng. Bài tập vận động nhẹ, không phải phương pháp chữa bệnh.")
    return {"hook": title, "series_id": series["id"], "series_title": series["title"], "move_n": move["n"],
            "careful": careful, "caption": caption, "hashtags": series.get("hashtags", [])[:5],
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


def write_prompts(series: dict, move: dict) -> Path:
    """prompts_NN.txt with one Gemini-app video prompt per clip still missing for this move."""
    d, nn = _clip_dir(series), f"{move['n']:02d}"
    d.mkdir(parents=True, exist_ok=True)
    look = ("Realistic vertical 9:16 video, full body visible from head to feet, front view, static camera on a "
            "tripod at chest height, slow smooth tai chi tempo, natural light. No text, no captions, no music, "
            "no other people.")
    wanted = []
    if not (d / "00.mp4").exists() and series.get("ready_en"):
        wanted.append(("00.mp4", "Tư thế chuẩn bị (dùng chung cho mọi bài)", series["ready_en"]))
    for k, (vi, en) in enumerate(zip(move["steps"], move.get("steps_en", [])), 1):
        if not (d / f"{nn}_{k}.mp4").exists():
            wanted.append((f"{nn}_{k}.mp4", f"Bước {k}: {vi}", en))
    lines = [f"PROMPT VIDEO CHO APP GEMINI — {series['title']} bài {move['n']}: {move['name']}",
             "",
             "Cách làm:",
             "1. Mở gemini.google.com (hoặc app Gemini) → chọn tạo video.",
             "2. Dán từng prompt bên dưới (mỗi prompt 1 video). Dùng cùng một cuộc trò chuyện để nhân vật giống nhau.",
             "3. Xem kỹ: tay, chân, hướng nhìn có đúng như dòng tiếng Việt không. Sai thì tạo lại.",
             f"4. Tải video về, đổi tên đúng như dòng 'Lưu thành', bỏ vào thư mục {d}/",
             "5. Đủ clip thì chạy lại: .venv/bin/python demo.py --exercise",
             "   (Hết lượt tạo video trong ngày thì làm các bước lẻ 1, 3 trước: bước thiếu clip dùng clip bước trước.)",
             ""]
    for name, vi, en in wanted:
        lines += ["=" * 70, f"Lưu thành: {name}", f"Động tác: {vi}", "",
                  f"{look} The person is {series.get('character_en', 'a calm middle-aged person')}. "
                  f"Over about eight seconds he {en}.", ""]
    if not wanted:
        lines.append("Đã đủ clip cho bài này.")
    path = d / f"prompts_{nn}.txt"
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

def _overlay(script: dict, i: int):
    """Transparent 1080x1920 layer with the texts for scene i (kept clear of TikTok's bottom UI)."""
    from PIL import Image, ImageDraw
    seg = script["segments"][i]
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
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


def render(script: dict, out_dir: Path) -> str:
    segs, clips = script["segments"], script["clips"]
    n = len(segs)
    inputs, filters, temp = [], [], []
    for i, seg in enumerate(segs):
        dur = seg["duration"] + demo.GAP + (demo.END_HOLD if i == n - 1 else 0)
        seg["scene_dur"] = dur
        ci = script["scene_clip"][i] if script.get("scene_clip") else i % len(clips)
        clip = out_dir / clips[ci]["file"]
        png = out_dir / f"_scene_{i}.png"
        _overlay(script, i).save(png)
        temp.append(png)
        # Short clips (Gemini makes ~8 s) are slowed a little to fit the narration; tai chi tempo hides it
        clip_secs = _clip_info(clip)[2] or dur
        slow = min(max(dur / clip_secs, 1.0), MAX_SLOWDOWN)
        inputs += ["-stream_loop", "-1", "-t", f"{dur / slow + 0.1:.3f}", "-i", str(clip)]
        inputs += ["-loop", "1", "-framerate", str(demo.FPS), "-t", f"{dur:.3f}", "-i", str(png)]
        v, o = 2 * i, 2 * i + 1
        # Blurred full-frame copy behind, clip in the box between the texts, texts on top
        top, box_h = VIDEO_BOX
        filters.append(
            f"[{v}:v]setpts={slow:.3f}*PTS,fps={demo.FPS},split=2[bgs{i}][fgs{i}];"
            f"[bgs{i}]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
            f"boxblur=25:2,eq=brightness=-0.18[bg{i}];"
            f"[fgs{i}]{_fg_filter(clip)}[fg{i}];"
            f"[bg{i}][fg{i}]overlay=(W-w)/2:{top}+({box_h}-h)/2[base{i}];"
            f"[base{i}][{o}:v]overlay=0:0,setsar=1,format=yuv420p,trim=duration={dur:.3f}[v{i}]")
        print(f"   Scene {i + 1} [{seg['kind']}]: {dur:.1f}s  {clips[ci]['source']}"
              + (f" (x{slow:.2f} slower)" if slow > 1.01 else ""))
    base = 2 * n
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
    for p in temp:
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


def finish(out_dir: Path, script: dict, skip_approval: bool) -> dict:
    video_path = render(script, out_dir)
    (out_dir / "script.json").write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")
    if not skip_approval and not demo.approval_step(script, video_path):
        print("❌ Rejected — files kept. Re-render without new voice calls: "
              f"python demo.py --exercise-rerender {out_dir}")
        return {"status": "rejected", "dir": str(out_dir)}
    write_post_kit(out_dir, script)
    mark_done(script["series_id"], script["move_n"])
    print(f"📚 Curriculum: {script['series_title']} bài {script['move_n']} → done")
    result = {"status": "ready_for_manual_upload", "dir": str(out_dir)}
    if os.environ.get("DRIVE_FOLDER_ID"):
        result.update(demo.move_to_drive(out_dir, f"Bài tập - {script['series_title']}"))
    return result


def run_next(base_dir: Path, skip_approval: bool, allow_stock: bool = False) -> dict:
    cur = load_curriculum()
    series, move = next_move(cur)
    if not move:
        raise RuntimeError("No move left with steps written — add steps to the next move in "
                           f"{CURRICULUM}")
    files = scene_clip_files(series, move)
    if files is None and not allow_stock:
        # Stop before any voice call: the clips for this move have to be made in the Gemini app first
        prompts = write_prompts(series, move)
        print(f"🎞️  {series['title']} bài {move['n']} chưa có clip. Làm clip theo {prompts}")
        return {"status": "needs_clips", "dir": str(prompts)}
    if files is not None:
        write_prompts(series, move)  # keeps the list of clips still missing up to date
    script = build_script(cur, series, move)
    out_dir = base_dir / f"{datetime.now():%Y%m%d_%H%M%S}_baitap_{series['id']}_{move['n']:02d}"
    out_dir.mkdir(parents=True, exist_ok=True)
    print("\n" + "=" * 60)
    print(f"🧘 {series['title']} — bài {move['n']}: {move['name']}")
    print("=" * 60)

    if files is not None:
        script["clips"], script["scene_clip"] = copy_scene_clips(files, out_dir)
        script["stock"] = False
    else:
        script["clips"] = download_clips(pick_clips(series, move["n"]), out_dir)
        script["stock"] = True
    persona = demo.choose_persona({"category": "tập luyện"})
    model = os.environ.get("EXERCISE_TTS_MODEL", DEFAULT_TTS_MODEL)
    demo.generate_voiceovers(script["segments"], out_dir, persona, model)
    script["voice_persona"] = persona
    return finish(out_dir, script, skip_approval)


def rerender(out_dir: Path, skip_approval: bool) -> dict:
    script = json.loads((out_dir / "script.json").read_text(encoding="utf-8"))
    return finish(out_dir, script, skip_approval)
