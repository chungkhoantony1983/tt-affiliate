"""
Studio API — review and edit rendered videos from the local web page /studio (DR-0001).

Rule C-0001-2: every video operation lives in demo.py. This module only reads/writes
script.json, product.json and uploaded images, and runs demo.py in a subprocess:
  demo.py --render-only DIR [--revoice-all edge]
  demo.py --approve DIR

Rule C-0001-3: write endpoints require the X-Studio header, which is not allowed by CORS,
so other web pages cannot call them from the browser.
"""
import io
import json
import os
import re
import subprocess
import sys
import threading
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter(prefix="/api/studio", tags=["studio"])

REPO_ROOT = Path(__file__).resolve().parents[3]
DEMO = REPO_ROOT / "demo.py"
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")
PIL_FORMATS = {"PNG": ".png", "JPEG": ".jpg", "MPO": ".jpg", "WEBP": ".webp"}
MAX_UPLOAD = 15 * 1024 * 1024
MAX_PRODUCT_IMAGES = 3  # demo.render_video uses the first 3
SERVED_FILE = re.compile(r"^(canh_\d+|anh_sp_\d+|img_\d+)\.(png|jpg|jpeg|webp)$")
LOCAL_HOSTS = {"127.0.0.1", "localhost"}

# demo.py exit codes (EXIT_REVOICE_FAILED, EXIT_NOT_READY)
ERROR_KINDS = {3: "revoice", 4: "not_ready"}


# ---------------------------------------------------------------------------
# Folders
# ---------------------------------------------------------------------------

def _videos_root() -> Path:
    storage = Path(settings.STORAGE_PATH)
    return (storage if storage.is_absolute() else REPO_ROOT / storage) / "videos"


def _logs_root() -> Path:
    # Outside the video folder: approving uploads the whole folder to Drive and may delete it.
    return _videos_root().parent / "studio-logs"


def _folders() -> List[Path]:
    root = _videos_root()
    if not root.is_dir():
        return []
    return sorted((p for p in root.iterdir() if (p / "video.mp4").is_file()),
                  key=lambda p: p.name, reverse=True)


def _folder_or_404(name: str) -> Path:
    for folder in _folders():
        if folder.name == name:
            return folder
    raise HTTPException(status_code=404, detail="Không tìm thấy video này")


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _write_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _editable(folder: Path) -> bool:
    """Folders made by demo.py. Exercise videos made outside the repo (no product.json) are view-only."""
    script = _read_json(folder / "script.json")
    return (folder / "product.json").is_file() and bool(script.get("segments"))


def _title(folder: Path, product: dict, script: dict) -> str:
    """Product name; for view-only folders the first caption line, else the folder name without its timestamp."""
    if product.get("name"):
        return product["name"]
    caption = (script.get("caption") or "").strip().splitlines()
    if caption:
        return caption[0][:60]
    return re.sub(r"^\d{8}_\d{6}_", "", folder.name).replace("-", " ").replace("_", " ") or folder.name


def _label(folder: Path) -> str:
    if not _editable(folder):
        return "view_only"
    if (folder / "prompts.txt").is_file():
        return "needs_images"
    if (folder / "post.txt").is_file():
        return "approved"
    return "review"


def _scene_image(folder: Path, index: int) -> Optional[str]:
    for ext in IMAGE_EXTS:
        if (folder / f"canh_{index + 1}{ext}").is_file():
            return f"canh_{index + 1}{ext}"
    return None


def _image_prompts(folder: Path) -> dict:
    """Scene number → prompt text to paste into the Gemini app, read from prompts.txt."""
    path = folder / "prompts.txt"
    if not path.is_file():
        return {}
    prompts, scene, body = {}, None, []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^CẢNH (\d+) —", line)
        if m:
            scene, body = int(m.group(1)), []
        elif scene is not None and line.startswith("="):
            prompts[scene] = "\n".join(body).strip()
            scene = None
        elif scene is not None and not line.startswith("-" * 10):
            body.append(line)
    if scene is not None:
        prompts[scene] = "\n".join(body).strip()
    return prompts


def _file_url(folder: Path, name: str) -> str:
    stamp = int((folder / name).stat().st_mtime)
    return f"/api/studio/videos/{folder.name}/files/{name}?v={stamp}"


def _product_images(folder: Path, product: dict) -> list:
    items = []
    for k, src in enumerate((product.get("images") or [])[:MAX_PRODUCT_IMAGES]):
        local = src if SERVED_FILE.match(src or "") and (folder / src).is_file() else None
        cached = f"img_{k}.jpg" if (folder / f"img_{k}.jpg").is_file() else None
        if local:
            url = _file_url(folder, local)
        elif src.startswith(("http://", "https://")):
            url = _file_url(folder, cached) if cached else src
        else:
            url = None  # a path elsewhere on this computer
        items.append({"slot": k, "url": url, "uploaded": bool(local)})
    return items


def _voice_engine(script: dict) -> tuple:
    """(engine, known). Folders made before DR-0001 have no tts_provider: guess like demo.tts_provider()."""
    if script.get("tts_provider"):
        return script["tts_provider"], True
    guess = (settings.TTS_PROVIDER or ("gemini" if settings.GEMINI_API_KEY else "edge")).strip().lower()
    return guess, False


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------

def require_studio(request: Request, x_studio: Optional[str] = Header(None)) -> None:
    """CSRF + DNS-rebinding guard for write endpoints."""
    if x_studio != "1" or request.url.hostname not in LOCAL_HOSTS:
        raise HTTPException(status_code=403, detail="Chỉ trang Studio trên máy này được sửa video")


def _editable_or_409(folder: Path) -> None:
    if not _editable(folder):
        raise HTTPException(status_code=409, detail="Video này chỉ xem được, không sửa được trên Studio")


# ---------------------------------------------------------------------------
# Background job (one at a time)
# ---------------------------------------------------------------------------

_job_lock = threading.Lock()
_job: dict = {}
_proc: Optional[subprocess.Popen] = None


def _job_running() -> bool:
    return _proc is not None and _proc.poll() is None


def _no_job_or_409() -> None:
    if _job_running():
        raise HTTPException(status_code=409, detail="Đang có việc chạy, đợi xong rồi thử lại")


def _start_job(action: str, folder: Path, args: list) -> dict:
    global _proc
    with _job_lock:
        _no_job_or_409()
        _logs_root().mkdir(parents=True, exist_ok=True)
        log_path = _logs_root() / f"{folder.name}.log"
        log = open(log_path, "w", encoding="utf-8")
        env = {**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"}
        try:
            _proc = subprocess.Popen([sys.executable, str(DEMO), *args, str(folder)],
                                     cwd=str(REPO_ROOT), stdout=log, stderr=subprocess.STDOUT, env=env)
        finally:
            log.close()  # the child keeps its own handle
        _job.clear()
        _job.update(action=action, folder=folder.name, log=str(log_path))
        return job_status()


def _log_lines(path: str, n: int = 40) -> list:
    try:
        lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    return [line for line in lines if line.strip()][-n:]


@router.get("/job")
def job_status():
    if not _job:
        return {"state": "idle"}
    lines = _log_lines(_job["log"])
    status = {"action": _job["action"], "folder": _job["folder"], "log": lines[-15:]}
    if _job_running():
        return {**status, "state": "running"}
    code = _proc.returncode if _proc else -1
    if code == 0:
        drive = next((line.split("Drive:", 1)[1].strip() for line in lines if "Drive:" in line), None)
        return {**status, "state": "done", "drive_link": drive,
                "folder_kept": (_videos_root() / _job["folder"]).is_dir()}
    return {**status, "state": "error", "error_kind": ERROR_KINDS.get(code, "failed")}


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

@router.get("/videos")
def list_videos():
    items = []
    for folder in _folders():
        product = _read_json(folder / "product.json")
        items.append({
            "folder": folder.name,
            "title": _title(folder, product, _read_json(folder / "script.json")),
            "label": _label(folder),
            "updated": int((folder / "video.mp4").stat().st_mtime),
        })
    return {"videos": items, "drive": bool(settings.DRIVE_FOLDER_ID)}


@router.get("/videos/{folder}")
def video_detail(folder: str):
    path = _folder_or_404(folder)
    script = _read_json(path / "script.json")
    product = _read_json(path / "product.json")
    hashtags = " ".join(script.get("hashtags") or [])
    detail = {
        "folder": path.name,
        "title": _title(path, product, script),
        "label": _label(path),
        "video_url": f"/api/studio/videos/{path.name}/video?v={int((path / 'video.mp4').stat().st_mtime)}",
        "caption": (script.get("caption") or "").strip(),
        "hashtags": hashtags,
        "post_text": f"{(script.get('caption') or '').strip()} {hashtags}".strip(),
        "drive": bool(settings.DRIVE_FOLDER_ID),
    }
    if detail["label"] == "view_only":
        return detail

    engine, known = _voice_engine(script)
    prompts = _image_prompts(path)
    segments = []
    for i, seg in enumerate(script["segments"]):
        image = _scene_image(path, i) if seg.get("kind") == "story" else None
        segments.append({
            "index": i,
            "kind": seg.get("kind", "product"),
            "speaker": seg.get("speaker", "narrator"),
            "line": seg.get("line", ""),
            "audio_line": seg.get("audio_line") or seg.get("line", ""),
            "text": seg.get("text", ""),
            "image_url": _file_url(path, image) if image else None,
            "image_prompt": prompts.get(i + 1, ""),
        })
    return {
        **detail,
        "hook": script.get("hook", ""),
        "price": int(product.get("price") or 0),
        "style": script.get("style", ""),
        "segments": segments,
        "product_images": _product_images(path, product),
        "voice_engine": engine,
        "voice_engine_known": known,
        "needs_render": bool(script.get("needs_render")),
    }


@router.get("/videos/{folder}/video")
def video_file(folder: str):
    return FileResponse(_folder_or_404(folder) / "video.mp4", media_type="video/mp4",
                        headers={"Cache-Control": "no-store"})


@router.get("/videos/{folder}/files/{name}")
def folder_file(folder: str, name: str):
    path = _folder_or_404(folder)
    if not SERVED_FILE.match(name) or not (path / name).is_file():
        raise HTTPException(status_code=404, detail="Không có ảnh này")
    return FileResponse(path / name, headers={"Cache-Control": "no-store"})


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------

class SegmentEdit(BaseModel):
    line: str
    text: str = ""


class VideoEdit(BaseModel):
    caption: Optional[str] = None
    hashtags: Optional[str] = None
    hook: Optional[str] = None
    price: Optional[int] = None
    segments: Optional[List[SegmentEdit]] = None


def _clean_hashtags(raw: str) -> list:
    tags = []
    for word in re.split(r"[\s,]+", raw or ""):
        word = word.strip().lstrip("#")
        if word:
            tags.append("#" + word)
    return list(dict.fromkeys(tags))


@router.put("/videos/{folder}", dependencies=[Depends(require_studio)])
def save_video(folder: str, edit: VideoEdit):
    path = _folder_or_404(folder)
    _editable_or_409(path)
    _no_job_or_409()
    script = _read_json(path / "script.json")
    product = _read_json(path / "product.json")
    needs_render = False

    if edit.caption is not None:
        script["caption"] = edit.caption.strip()
    if edit.hashtags is not None:
        script["hashtags"] = _clean_hashtags(edit.hashtags)
    if edit.hook is not None and edit.hook.strip() != (script.get("hook") or ""):
        script["hook"] = edit.hook.strip()
        needs_render = True
    if edit.price is not None:
        if edit.price < 0:
            raise HTTPException(status_code=400, detail="Giá không được âm")
        if edit.price != int(product.get("price") or 0):
            product["price"] = edit.price
            needs_render = True
    if edit.segments is not None:
        segments = script["segments"]
        if len(edit.segments) != len(segments):
            raise HTTPException(status_code=400, detail="Số cảnh không khớp, hãy tải lại trang")
        for i, (seg, new) in enumerate(zip(segments, edit.segments)):
            line = re.sub(r"\s+", " ", new.line).strip()
            if not line:
                raise HTTPException(status_code=400, detail=f"Cảnh {i + 1}: lời đọc không được để trống")
            if len(line) > 300:
                raise HTTPException(status_code=400, detail=f"Cảnh {i + 1}: lời đọc quá dài")
            text = new.text.strip()
            if line != seg.get("line") or text != (seg.get("text") or ""):
                seg.setdefault("audio_line", seg.get("line", ""))  # folders made before DR-0001
                seg["line"], seg["text"] = line, text
                needs_render = True

    if needs_render:
        script["needs_render"] = True
    _write_json(path / "script.json", script)
    _write_json(path / "product.json", product)
    return video_detail(folder)


def _sniff_image(data: bytes) -> str:
    from PIL import Image

    try:
        with Image.open(io.BytesIO(data)) as im:
            fmt = im.format
            im.verify()
    except Exception:
        fmt = None
    if fmt not in PIL_FORMATS:
        raise HTTPException(status_code=400, detail="Chỉ nhận ảnh PNG, JPG hoặc WEBP")
    return PIL_FORMATS[fmt]


def _replace_image(folder: Path, stem: str, ext: str, data: bytes) -> str:
    for old in IMAGE_EXTS:
        (folder / f"{stem}{old}").unlink(missing_ok=True)
    (folder / f"{stem}{ext}").write_bytes(data)
    return f"{stem}{ext}"


@router.post("/videos/{folder}/image", dependencies=[Depends(require_studio)])
async def upload_image(folder: str, target: str, index: int, request: Request):
    """Raw image bytes in the body. target=scene: index = scene (segment) index, saved as canh_{index+1}.
    target=product: index = product image slot 0-2, saved as anh_sp_{index+1} and set in product.json."""
    path = _folder_or_404(folder)
    _editable_or_409(path)
    _no_job_or_409()
    if int(request.headers.get("content-length") or 0) > MAX_UPLOAD:
        raise HTTPException(status_code=413, detail="Ảnh quá lớn (tối đa 15 MB)")
    data = await request.body()
    if len(data) > MAX_UPLOAD:
        raise HTTPException(status_code=413, detail="Ảnh quá lớn (tối đa 15 MB)")
    script = _read_json(path / "script.json")

    if target == "scene":
        segments = script["segments"]
        if not 0 <= index < len(segments) or segments[index].get("kind") != "story":
            raise HTTPException(status_code=400, detail="Cảnh này không dùng ảnh nhân vật")
        _replace_image(path, f"canh_{index + 1}", _sniff_image(data), data)
    elif target == "product":
        product = _read_json(path / "product.json")
        images = list(product.get("images") or [])
        if not 0 <= index <= min(len(images), MAX_PRODUCT_IMAGES - 1):
            raise HTTPException(status_code=400, detail="Vị trí ảnh sản phẩm không hợp lệ")
        name = _replace_image(path, f"anh_sp_{index + 1}", _sniff_image(data), data)
        if index == len(images):
            images.append(name)
        else:
            images[index] = name
        product["images"] = images
        _write_json(path / "product.json", product)
    else:
        raise HTTPException(status_code=400, detail="target phải là scene hoặc product")

    script["needs_render"] = True
    _write_json(path / "script.json", script)
    return video_detail(folder)


class RenderRequest(BaseModel):
    revoice_all: Optional[str] = None  # "edge": re-voice every line with the free voice


@router.post("/videos/{folder}/render", dependencies=[Depends(require_studio)])
def render(folder: str, req: RenderRequest = RenderRequest()):
    path = _folder_or_404(folder)
    _editable_or_409(path)
    args = ["--render-only"]
    if req.revoice_all:
        if req.revoice_all != "edge":
            raise HTTPException(status_code=400, detail="Chỉ hỗ trợ đọc lại toàn bộ bằng giọng edge")
        args = ["--revoice-all", "edge", "--render-only"]
    return _start_job("render", path, args)


@router.post("/videos/{folder}/approve", dependencies=[Depends(require_studio)])
def approve(folder: str):
    path = _folder_or_404(folder)
    _editable_or_409(path)
    if _read_json(path / "script.json").get("needs_render"):
        raise HTTPException(status_code=409, detail="Bạn đã sửa video, hãy bấm Dựng lại video trước khi duyệt")
    if _label(path) == "needs_images":
        raise HTTPException(status_code=409, detail="Còn cảnh chưa có ảnh nhân vật, chưa duyệt được")
    return _start_job("approve", path, ["--approve"])
