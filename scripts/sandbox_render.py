"""
Re-render a video folder on a throwaway copy (DR-0004, skill sandbox-render).

  PY=$(git rev-parse --path-format=absolute --git-common-dir)/../.venv/bin/python
  $PY scripts/sandbox_render.py storage/videos/<folder> [--revoice-all-edge] [--keep]

What it guarantees (C-0004-2):
  - The folder is copied to a new temp dir T (T/storage/videos/<folder>); only the copy is rendered.
    The original folder is hashed before and after (`original_unchanged` in the output).
  - The render runs with cwd = T: there is no .env and no google-credentials.json there, so no key
    is loaded and the sheet is never touched. The child environment also sets
    GEMINI_API_KEY= GROQ_API_KEY= PIXABAY_API_KEY= DRIVE_FOLDER_ID= SPREADSHEET_ID= TTS_PROVIDER=edge
    APPROVAL_MODE=web IMAGE_PROVIDER=manual (no Gemini, Groq, Pixabay or image API call).
  - No Gemini call: `demo.revoice_changed()` re-voices edited lines with `script.json -> tts_provider`,
    not with TTS_PROVIDER (DR-0004 R-3). So a product folder with an edited line
    (`line != audio_line`) is refused before anything is copied, unless --revoice-all-edge is given
    (then every line is re-voiced with edge-tts, free; `tts_provider` becomes "edge" in the copy).

Product video (folder has product.json):
  Runs `demo.py --render-only <copy>` as a subprocess (same as the Studio, C-0001-2), with
  `--revoice-all edge` when --revoice-all-edge is given. Relative image paths in product.json that
  are not inside the folder are copied into T under the same relative path (resolved against the
  repo that holds the folder, i.e. the parent of storage/videos/). Image URLs are still downloaded
  by demo.py (free). Expected status: "review" (or "needs_images" for a story video without images).
  Note: a folder without `tts_provider` counts as Gemini in `clean_gemini_audio`, which may re-trim
  the copy's audio locally (ffmpeg only, no network), so `audio_changed` can list files.

Travel video (topic.json, no product.json): refused (exit 2). Not supported by sandbox-render yet
(see TODO.md); use the environment block of the dev-selfcheck skill on a manual copy instead.

Exercise video (no product.json, script.json has series_id):
  Copies content/exercise_curriculum.json (this checkout first, else the folder's repo) and
  storage/clips/<series_id>/ (the folder's repo first, else this checkout) into T, imports demo and
  exercise from this checkout and patches: demo.approval_step -> False (no y/n prompt),
  exercise.mark_done / demo.move_to_drive / every TTS function -> raise. Then calls
  exercise.rerender(copy, skip_approval=False). Expected status: "rejected" right after the render,
  so the curriculum and Drive are never reached. `repo_data_unchanged` hashes the source curriculum
  and clips before and after. --revoice-all-edge is not supported for exercise videos.

Output: render log on stderr (also T/render.log), then one JSON object on stdout:
  {"kind", "sandbox_dir", "kept", "status", "video", "duration_s", "audio_changed",
   "post_txt_existed", "post_txt_created", "original_unchanged", "exit_code", ...}
  post_txt_created = post.txt of the copy was created or rewritten by the render (the approval step
  was reached); a post.txt that was already in the folder and is left as is (exercise) or deleted
  (demo.py --render-only asks for a new approval) does not count. post_txt_existed = the copy had
  a post.txt before the render (copied from the original).
T is deleted at the end unless --keep (keep it to run audio_seams.py / transcript_check.py on it),
also on Ctrl-C / SIGTERM. A product render is killed after RENDER_TIMEOUT_S (540 s, under the 600 s
Bash tool limit) together with its whole process group (ffmpeg children included).

Exit codes: 0 = rendered with the expected status, no post.txt written and the original unchanged;
            1 = render failed or timed out, unexpected status, post.txt written, or the original changed;
            2 = refused before running (bad path, no script.json, edited lines without
                --revoice-all-edge, travel folder, read-only folder, unsupported option).
"""
import argparse
import contextlib
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

CODE_ROOT = Path(__file__).resolve().parent.parent   # checkout whose demo.py / exercise.py are tested
SAFE_ENV = {"GEMINI_API_KEY": "", "GROQ_API_KEY": "", "PIXABAY_API_KEY": "",
            "DRIVE_FOLDER_ID": "", "SPREADSHEET_ID": "", "TTS_PROVIDER": "edge", "APPROVAL_MODE": "web",
            "IMAGE_PROVIDER": "manual", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUNBUFFERED": "1"}
EXIT_OK, EXIT_FAILED, EXIT_REFUSED = 0, 1, 2
# A product render takes 1-3 min (edge-tts retries included). Kept under 600 s, the longest a
# foreground Bash tool call may run, so the script cleans up before the caller gives up on it.
RENDER_TIMEOUT_S = 540
_child = None   # running demo.py (own process group), killed with its group on timeout or signal


class Refused(Exception):
    """Stop before copying or rendering anything."""


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def kill_group(proc) -> None:
    """SIGKILL the whole process group of proc (demo.py and the ffmpeg / edge-tts it started)."""
    if proc is None:
        return
    try:
        os.killpg(proc.pid, signal.SIGKILL)   # the group outlives demo.py if ffmpeg is still running
    except (ProcessLookupError, PermissionError):
        pass


def _on_signal(signum, _frame):
    """SIGTERM / SIGINT: stop the child group, then exit through main()'s finally (temp dir removed)."""
    kill_group(_child)
    log(f"sandbox_render: got signal {signum}, stopping")
    sys.exit(128 + signum)


def file_hash(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def tree_hashes(root: Path) -> dict:
    """sha256 of every file under root (relative path -> hex); a single file is hashed as itself."""
    if root.is_file():
        return {root.name: hashlib.sha256(root.read_bytes()).hexdigest()}
    out = {}
    if root.is_dir():
        for p in sorted(root.rglob("*")):
            if p.is_file():
                out[str(p.relative_to(root))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def source_root(folder: Path) -> Path:
    """Repo that holds the folder (<root>/storage/videos/<folder>); else the current directory."""
    if folder.parent.name == "videos" and folder.parent.parent.name == "storage":
        return folder.parent.parent.parent
    return Path.cwd()


def edited_scenes(script: dict) -> list:
    """1-based scene numbers whose line differs from the line their audio was made from
    (same test as demo.revoice_changed)."""
    return [i + 1 for i, s in enumerate(script.get("segments") or [])
            if (s.get("line") or "").strip() != (s.get("audio_line") or s.get("line") or "").strip()]


def video_duration(path: Path):
    if not path.is_file():
        return None
    import imageio_ffmpeg
    err = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-i", str(path)],
                         capture_output=True, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err)
    return round(int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]), 2) if m else None


def audio_hashes(folder: Path) -> dict:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.glob("audio_*.mp3"))}


def copy_product_images(product: dict, src_root: Path, sandbox: Path, folder: Path) -> list:
    """Copy relative image paths that demo.py would resolve against its cwd into the sandbox."""
    copied = []
    for img in product.get("images") or []:
        if not isinstance(img, str) or not img or img.startswith(("http://", "https://")):
            continue
        rel = Path(img)
        if rel.is_absolute() or (folder / rel).is_file():
            continue  # absolute paths are read in place; files inside the folder come with the copy
        src = (src_root / rel).resolve()
        dest = (sandbox / rel).resolve()
        if sandbox.resolve() not in dest.parents:
            log(f"   ! image path leaves the sandbox, not copied: {img}")
            continue
        if not src.is_file():
            log(f"   ! image not found, not copied: {src}")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        copied.append(img)
    return copied


def run_product(copy: Path, revoice_all_edge: bool, sandbox: Path, log_path: Path) -> tuple:
    """demo.py --render-only on the copy, as a subprocess with cwd = sandbox. Returns (exit, status)."""
    cmd = [sys.executable, str(CODE_ROOT / "demo.py"), "--render-only", str(copy)]
    if revoice_all_edge:
        cmd += ["--revoice-all", "edge"]
    env = {**os.environ, **SAFE_ENV}
    log(f"$ (cwd {sandbox}) {' '.join(cmd)}")
    global _child
    status, lines = None, []
    with open(log_path, "a", encoding="utf-8") as lf:
        # own session = own process group: a timeout or a signal kills the ffmpeg children too
        proc = subprocess.Popen(cmd, cwd=str(sandbox), env=env, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
                                start_new_session=True)
        _child = proc
        fired = threading.Event()

        def on_timeout():
            fired.set()
            kill_group(proc)

        # edge-tts has no timeout of its own and the free endpoint sometimes stalls forever
        watchdog = threading.Timer(RENDER_TIMEOUT_S, on_timeout)
        watchdog.start()
        code = None
        try:
            for line in proc.stdout:
                sys.stderr.write(line)
                lf.write(line)
                lines.append(line.rstrip("\n"))
            code = proc.wait()
        finally:
            watchdog.cancel()
            kill_group(proc)   # on every exit path (signal, error, timeout) no child is left behind
            _child = None
    timed_out = fired.is_set()
    if timed_out:
        log(f"sandbox_render: demo.py and its process group killed after {RENDER_TIMEOUT_S} s "
            f"(stalled edge-tts or ffmpeg?)")
    # demo.py prints "<status padded to 24> <dir>" as the last result line
    for line in reversed(lines):
        m = re.match(r"^(\w+)\s+\S", line)
        if m and line.rstrip().endswith(str(copy)):
            status = m[1]
            break
    return code, status, timed_out


def run_exercise(copy: Path, script: dict, src_root: Path, sandbox: Path, log_path: Path) -> dict:
    """exercise.rerender on the copy inside this process, with approval, curriculum and Drive blocked."""
    series_id = script["series_id"]
    cur_src = next((p for p in (CODE_ROOT / "content/exercise_curriculum.json",
                                src_root / "content/exercise_curriculum.json") if p.is_file()), None)
    clips_src = next((p for p in (src_root / "storage/clips" / series_id,
                                  CODE_ROOT / "storage/clips" / series_id) if p.is_dir()), None)
    if cur_src:
        (sandbox / "content").mkdir(parents=True, exist_ok=True)
        shutil.copy2(cur_src, sandbox / "content/exercise_curriculum.json")
    else:
        log("   ! no content/exercise_curriculum.json found: the render uses the clips already in the folder")
    if clips_src:
        shutil.copytree(clips_src, sandbox / "storage/clips" / series_id)
    else:
        log(f"   ! no storage/clips/{series_id}/ found: the render uses the clips already in the folder")
    watched = [p for p in (cur_src, clips_src) if p]
    before = {str(p): tree_hashes(p) for p in watched}

    os.environ.update(SAFE_ENV)
    os.chdir(sandbox)
    sys.path.insert(0, str(CODE_ROOT))
    import demo
    import exercise

    def blocked(name):
        def _raise(*_a, **_k):
            raise RuntimeError(f"sandbox_render: {name} is blocked in the sandbox")
        return _raise

    def no_approval(_script, video_path):
        print(f"sandbox_render: approval skipped (treated as rejected): {video_path}")
        return False

    demo.approval_step = no_approval
    demo.move_to_drive = blocked("demo.move_to_drive")
    exercise.mark_done = blocked("exercise.mark_done")
    for fn in ("_gemini_tts", "_tts", "generate_voiceovers", "revoice_changed"):
        setattr(demo, fn, blocked(f"demo.{fn}"))
    exercise.CURRICULUM = sandbox / "content/exercise_curriculum.json"
    exercise.LOCAL_CLIPS = sandbox / "storage/clips"
    exercise.PIXABAY_CACHE = sandbox / "storage/pixabay_cache"

    error = None
    with open(log_path, "a", encoding="utf-8") as lf:
        class Tee:
            def write(self, s):
                sys.stderr.write(s)
                lf.write(s)
                return len(s)

            def flush(self):
                sys.stderr.flush()
                lf.flush()

        with contextlib.redirect_stdout(Tee()):
            try:
                result = exercise.rerender(copy, skip_approval=False)
            except Exception as e:  # report, do not hide: the JSON says status=error
                result = {"status": "error"}
                error = f"{type(e).__name__}: {e}"
                print(f"sandbox_render: render failed: {error}")
    os.chdir(CODE_ROOT)
    after = {str(p): tree_hashes(p) for p in watched}
    out = {"status": result.get("status"), "repo_data_unchanged": before == after,
           "repo_data_checked": [str(p) for p in watched],
           "curriculum_source": str(cur_src) if cur_src else None,
           "clips_source": str(clips_src) if clips_src else None}
    if error:
        out["error"] = error
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Re-render a video folder on a temp copy: no Gemini, no approval, no Drive, no Sheet, "
                    "no curriculum write. Prints one JSON object on stdout.")
    ap.add_argument("folder", help="video folder, e.g. storage/videos/<folder> (only read, never modified)")
    ap.add_argument("--revoice-all-edge", action="store_true",
                    help="product video: re-voice every line with edge-tts (needed when a line was edited)")
    ap.add_argument("--keep", action="store_true", help="keep the temp dir (path in sandbox_dir)")
    args = ap.parse_args()
    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)

    folder = Path(args.folder).expanduser().resolve()
    sandbox = None
    try:
        if not folder.is_dir():
            raise Refused(f"Not a folder: {folder}")
        if not (folder / "script.json").is_file():
            raise Refused(f"No script.json in {folder}")
        script = json.loads((folder / "script.json").read_text(encoding="utf-8"))
        is_product = (folder / "product.json").is_file()
        if not is_product and (folder / "topic.json").is_file():
            raise Refused(f"{folder.name}: travel folder (topic.json) is not supported by sandbox-render yet "
                          f"(see TODO.md). Use the environment block of the dev-selfcheck skill on a copy "
                          f"in a temp dir instead.")
        if not is_product and not script.get("series_id"):
            raise Refused(f"{folder.name}: no product.json and no series_id in script.json (read-only folder)")
        if not is_product and args.revoice_all_edge:
            raise Refused("--revoice-all-edge is only for product videos (exercise videos keep their voice)")
        edited = edited_scenes(script)
        if is_product and edited and not args.revoice_all_edge:
            raise Refused(f"Scenes {edited} have an edited line (line != audio_line). Re-voicing them would use "
                          f"tts_provider={script.get('tts_provider') or 'gemini?'} from script.json, which may "
                          f"call Gemini. Run again with --revoice-all-edge to re-voice every line with edge-tts.")
    except Refused as e:
        log(f"sandbox_render: refused: {e}")
        print(json.dumps({"status": "refused", "error": str(e), "original_unchanged": True,
                          "exit_code": EXIT_REFUSED}, ensure_ascii=False, indent=2))
        return EXIT_REFUSED

    original_before = tree_hashes(folder)
    src_root = source_root(folder)
    sandbox = Path(tempfile.mkdtemp(prefix="sandbox_render_"))
    try:
        out = render_in_sandbox(folder, script, is_product, src_root, sandbox, original_before, args)
    finally:  # also on Ctrl-C or an unexpected error
        if not args.keep:
            shutil.rmtree(sandbox, ignore_errors=True)
            log(f"sandbox_render: removed {sandbox} (use --keep to keep it)")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return out["exit_code"]


def render_in_sandbox(folder: Path, script: dict, is_product: bool, src_root: Path, sandbox: Path,
                      original_before: dict, args) -> dict:
    copy = sandbox / "storage" / "videos" / folder.name
    shutil.copytree(folder, copy)
    log_path = sandbox / "render.log"
    log(f"sandbox_render: copy {folder} -> {copy}")
    audio_before = audio_hashes(copy)
    post_before = file_hash(copy / "post.txt")   # an exercise folder may already hold an approved post.txt

    out = {"kind": "product" if is_product else "exercise", "source": str(folder),
           "sandbox_dir": str(sandbox), "kept": args.keep, "copy": str(copy)}
    if is_product:
        product = json.loads((folder / "product.json").read_text(encoding="utf-8"))
        out["images_copied"] = copy_product_images(product, src_root, sandbox, folder)
        code, status, timed_out = run_product(copy, args.revoice_all_edge, sandbox, log_path)
        out.update({"status": "timeout" if timed_out else (status if code == 0 else (status or "error")),
                    "demo_exit_code": code, "timed_out": timed_out})
        expected = {"review", "needs_images"}
    else:
        out.update(run_exercise(copy, script, src_root, sandbox, log_path))
        expected = {"rejected"}

    audio_after = audio_hashes(copy)
    new_script = {}
    if (copy / "script.json").is_file():
        new_script = json.loads((copy / "script.json").read_text(encoding="utf-8"))
    video = copy / "video.mp4"
    post_after = file_hash(copy / "post.txt")
    out.update({
        "video": str(video) if video.is_file() else None,
        "duration_s": video_duration(video),
        "audio_changed": sorted(k for k in set(audio_before) | set(audio_after)
                                if audio_before.get(k) != audio_after.get(k)),
        "tts_provider": new_script.get("tts_provider"),
        "post_txt_existed": post_before is not None,
        # written by this render; demo.render_only deleting an old post.txt is normal (new approval needed)
        "post_txt_created": post_after is not None and post_after != post_before,
        "original_unchanged": tree_hashes(folder) == original_before,
        "log": str(log_path) if args.keep else None,
    })
    ok = (out["status"] in expected and out["original_unchanged"] and not out["post_txt_created"]
          and out.get("repo_data_unchanged", True))
    out["exit_code"] = EXIT_OK if ok else EXIT_FAILED
    return out


if __name__ == "__main__":
    sys.exit(main())
