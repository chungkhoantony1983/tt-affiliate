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
import shutil
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
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
DEMO = REPO_ROOT / "demo.py"
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")
PIL_FORMATS = {"PNG": ".png", "JPEG": ".jpg", "MPO": ".jpg", "WEBP": ".webp"}
MAX_UPLOAD = 15 * 1024 * 1024
MAX_PRODUCT_IMAGES = 3  # demo.render_video uses the first 3
SERVED_FILE = re.compile(r"^(canh_\d+|anh_sp_\d+|img_\d+)\.(png|jpg|jpeg|webp)$")
STAGING_FILE = re.compile(r"^anh_sp_[1-3]\.(png|jpg|jpeg|webp)$")
LOCAL_HOSTS = {"127.0.0.1", "localhost"}

# demo.py exit codes (EXIT_REVOICE_FAILED, EXIT_NOT_READY)
ERROR_KINDS = {3: "revoice", 4: "not_ready"}


def _validate_price(price: Optional[int]) -> Optional[int]:
    """Rule C-0007-2: only 0 (hide price) or integer >= 1000 VND is valid; reject < 0 and 1..999."""
    if price is None:
        return None
    if price < 0:
        raise HTTPException(status_code=400, detail="Giá không được âm")
    if 0 < price < 1000:
        raise HTTPException(
            status_code=400,
            detail="Giá đang dưới 1.000đ. Kiểm tra lại xem bạn có gõ thiếu 3 số 0 (ví dụ 189.000) không, hoặc nhập 0 nếu muốn ẩn giá.",
        )
    return int(price)


# ---------------------------------------------------------------------------
# Folders
# ---------------------------------------------------------------------------

def _videos_root() -> Path:
    storage = Path(settings.STORAGE_PATH)
    return (storage if storage.is_absolute() else REPO_ROOT / storage) / "videos"


def _logs_root() -> Path:
    # Outside the video folder: approving uploads the whole folder to Drive and may delete it.
    return _videos_root().parent / "studio-logs"


def _staging_root() -> Path:
    return _logs_root() / "staging"


def _slots_meta_path() -> Path:
    return _staging_root() / "slots.json"


def _read_slots_meta() -> dict:
    data = _read_json(_slots_meta_path())
    return {
        "preview": list(data.get("preview") or []),
        "overrides": dict(data.get("overrides") or {}),
    }


def _write_slots_meta(meta: dict) -> None:
    _staging_root().mkdir(parents=True, exist_ok=True)
    _write_json(_slots_meta_path(), meta)


def _clear_staging() -> None:
    root = _staging_root()
    if not root.is_dir():
        return
    for f in root.iterdir():
        if f.is_file():
            f.unlink(missing_ok=True)


def _studio_csv_path() -> str:
    env_csv = (os.environ.get("STUDIO_CSV_PATH") or "").strip()
    if env_csv:
        return env_csv
    default_videos = (REPO_ROOT / "storage" / "videos").resolve()
    if _videos_root().resolve() != default_videos:
        tmp_csv = _logs_root() / "products.csv"
        if not tmp_csv.is_file() and (REPO_ROOT / "products.csv").is_file():
            _logs_root().mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO_ROOT / "products.csv", tmp_csv)
        if tmp_csv.is_file():
            return str(tmp_csv)
    if (REPO_ROOT / "products.csv").is_file():
        return str(REPO_ROOT / "products.csv")
    return ""


def _open_sheet(tab: str = "Tiktok"):
    import product_sources

    sheet_ref = (os.environ.get("SPREADSHEET_ID") or settings.SPREADSHEET_ID or "").strip()
    creds_path = Path(settings.GOOGLE_APPLICATION_CREDENTIALS or "google-credentials.json")
    if not creds_path.is_absolute():
        creds_path = REPO_ROOT / creds_path
    csv_path = _studio_csv_path() if not (sheet_ref and creds_path.is_file()) else ""
    try:
        return product_sources.open_product_sheet(
            sheet_ref=sheet_ref,
            tab=tab,
            credentials=str(creds_path),
            csv_path=csv_path,
        )
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Chưa kết nối được Google Sheet. Bạn hãy kiểm tra cài đặt hoặc chuyển sang mục Dán link TikTok Shop.",
        )


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


def _start_create_job(spec: dict) -> dict:
    global _proc
    with _job_lock:
        _no_job_or_409()
        _logs_root().mkdir(parents=True, exist_ok=True)
        spec_path = _logs_root() / "create-input.json"
        _write_json(spec_path, spec)
        log_path = _logs_root() / "create.log"
        log = open(log_path, "w", encoding="utf-8")
        env = {**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"}
        try:
            _proc = subprocess.Popen(
                [sys.executable, str(DEMO), "--create-json", str(spec_path), "--output-dir", str(_videos_root())],
                cwd=str(REPO_ROOT),
                stdout=log,
                stderr=subprocess.STDOUT,
                env=env,
            )
        finally:
            log.close()
        _job.clear()
        _job.update(action="create", folder="", log=str(log_path))
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
    lines = _log_lines(_job["log"], n=80)
    folder = _job["folder"]
    if _job["action"] == "create":
        found = next(
            (line.split("Studio folder:", 1)[1].strip() for line in reversed(lines) if "Studio folder:" in line),
            None,
        )
        if found:
            folder = found
            _job["folder"] = found
    status = {"action": _job["action"], "folder": folder, "log": lines[-15:]}
    if _job_running():
        return {**status, "state": "running"}
    code = _proc.returncode if _proc else -1
    if code == 0:
        drive = next((line.split("Drive:", 1)[1].strip() for line in lines if "Drive:" in line), None)
        return {**status, "state": "done", "drive_link": drive,
                "folder_kept": bool(folder and (_videos_root() / folder).is_dir())}
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
        _validate_price(edit.price)
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


# ---------------------------------------------------------------------------
# Create new video (DR-0007)
# ---------------------------------------------------------------------------

class PreviewRequest(BaseModel):
    source: str = "url"  # "url" | "sheet"
    product_url: Optional[str] = None
    sheet_row: Optional[int] = None
    tab: str = "Tiktok"


class CreateVideoRequest(BaseModel):
    sheet_row: Optional[int] = None
    product_url: Optional[str] = None
    name: Optional[str] = None
    price: Optional[int] = None
    images: Optional[List[str]] = None
    style: str = "story"
    category: Optional[str] = None
    selling_points: Optional[str] = None
    notes: Optional[str] = None
    tab: str = "Tiktok"


@router.get("/sheet-rows")
def list_sheet_rows(tab: str = "Tiktok"):
    try:
        sheet = _open_sheet(tab)
    except HTTPException as e:
        return {"available": False, "rows": [], "message": e.detail}
    items = []
    for r in sheet.rows:
        name = (r.get("name") or "").strip()
        url = (r.get("product_url") or "").strip()
        if not name and not url:
            continue
        price = int(re.sub(r"[^\d]", "", r.get("price") or "0") or 0)
        status = (r.get("status") or "").strip()
        imgs = [x.strip() for x in (r.get("images") or "").split("|") if x.strip()]
        items.append({
            "row": int(r["_row"]),
            "name": name or url,
            "price": price,
            "product_url": url,
            "status": status,
            "has_video": status.lower() in ("done", "review", "needs_images"),
            "images_count": len(imgs),
        })
    return {"available": True, "rows": items}


@router.post("/product-preview", dependencies=[Depends(require_studio)])
def product_preview(req: PreviewRequest):
    import product_sources

    _no_job_or_409()
    _clear_staging()

    use_sheet = req.source == "sheet" or (req.sheet_row is not None and not (req.product_url or "").strip())
    if use_sheet:
        if req.sheet_row is None:
            raise HTTPException(
                status_code=400,
                detail="Hãy chọn một dòng hoặc nhập số dòng trên Google Sheet (bắt đầu từ dòng 2).",
            )
        if req.sheet_row == 1:
            raise HTTPException(
                status_code=400,
                detail="Dòng 1 là dòng tiêu đề cột. Hãy chọn từ dòng số 2 trở đi.",
            )
        if req.sheet_row < 1:
            raise HTTPException(
                status_code=400,
                detail="Số dòng không hợp lệ. Hãy chọn từ dòng số 2 trở đi.",
            )
        sheet = _open_sheet(req.tab)
        row = sheet.get_row(req.sheet_row)
        if not row or (not (row.get("name") or "").strip() and not (row.get("product_url") or "").strip()):
            raise HTTPException(
                status_code=400,
                detail=f"Dòng {req.sheet_row} đang trống hoặc không có sản phẩm. Hãy chọn dòng khác.",
            )
        name = (row.get("name") or "").strip()
        raw_price = (row.get("price") or "").strip()
        price = int(re.sub(r"[^\d]", "", raw_price) or 0) if raw_price != "" else None
        images = [x.strip() for x in (row.get("images") or "").split("|") if x.strip()][:MAX_PRODUCT_IMAGES]
        selling_points = [x.strip() for x in (row.get("selling_points") or "").split("|") if x.strip()]
        category = (row.get("category") or "").strip() or "Nhà cửa"
        notes = (row.get("notes") or "").strip()
        product_url = (row.get("product_url") or "").strip()
        warning = None

        if product_url and (not name or price is None or not images):
            try:
                info = product_sources.fetch_tiktok_product(product_url)
                if not name and info.get("title"):
                    name = info["title"].strip()
                if price is None and info.get("price"):
                    price = int(info["price"])
                if not images and info.get("images"):
                    images = list(info["images"][:MAX_PRODUCT_IMAGES])
                if not selling_points and info.get("description"):
                    selling_points = [
                        ln.lstrip("- ").strip() for ln in info["description"].splitlines() if ln.strip()
                    ][:5]
                if info.get("partial"):
                    warning = (
                        "Đã lấy được tên và 1 ảnh từ link TikTok. Bạn hãy kiểm tra lại Giá bán "
                        "và tải thêm ảnh sản phẩm (nếu có) trước khi bấm Tạo video."
                    )
            except Exception:
                warning = (
                    "TikTok tạm chặn đọc tự động từ link trên dòng này. Đã giữ nguyên thông tin có sẵn "
                    "trên bảng tính; bạn hãy kiểm tra thêm Tên, Giá bán và Ảnh sản phẩm ở bên dưới."
                )

        _write_slots_meta({"preview": images, "overrides": {}})
        return {
            "source": "sheet",
            "sheet_row": req.sheet_row,
            "product_url": product_url,
            "name": name,
            "price": price if price is not None else 0,
            "category": category,
            "images": images,
            "selling_points": "\n".join(selling_points),
            "description": "\n".join(selling_points),
            "notes": notes,
            "status": (row.get("status") or "").strip(),
            "partial": False,
            "blocked": False,
            "warning": warning,
        }

    url = (req.product_url or "").strip()
    if not url or not url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=400,
            detail="Hãy dán đường dẫn (link) sản phẩm TikTok Shop hợp lệ (bắt đầu bằng https://).",
        )
    try:
        info = product_sources.fetch_tiktok_product(url)
        images = list((info.get("images") or [])[:MAX_PRODUCT_IMAGES])
        _write_slots_meta({"preview": images, "overrides": {}})
        pts = [ln.lstrip("- ").strip() for ln in (info.get("description") or "").splitlines() if ln.strip()][:5]
        warning = None
        if info.get("partial"):
            warning = (
                "Đã lấy được tên và 1 ảnh từ link TikTok. Bạn hãy kiểm tra lại Giá bán "
                "và tải thêm ảnh sản phẩm (nếu có) trước khi bấm Tạo video."
            )
        return {
            "source": "url",
            "sheet_row": None,
            "product_url": url,
            "name": (info.get("title") or "").strip(),
            "price": int(info.get("price") or 0),
            "category": "Nhà cửa",
            "images": images,
            "selling_points": "\n".join(pts),
            "description": info.get("description") or "",
            "notes": "",
            "partial": bool(info.get("partial")),
            "blocked": False,
            "warning": warning,
        }
    except Exception:
        _write_slots_meta({"preview": [], "overrides": {}})
        return {
            "source": "url",
            "sheet_row": None,
            "product_url": url,
            "name": "",
            "price": 0,
            "category": "Nhà cửa",
            "images": [],
            "selling_points": "",
            "description": "",
            "notes": "",
            "partial": False,
            "blocked": True,
            "warning": (
                "TikTok tạm chặn đọc tự động từ link này. Bạn chỉ cần tự điền "
                "(1) Tên sản phẩm, (2) Giá bán và (3) Tải ảnh sản phẩm ở bên dưới "
                "rồi bấm Tạo video như bình thường."
            ),
        }


@router.post("/staging-image", dependencies=[Depends(require_studio)])
async def upload_staging_image(request: Request, slot: int = 0):
    _no_job_or_409()
    if not 0 <= slot < MAX_PRODUCT_IMAGES:
        raise HTTPException(status_code=400, detail="Vị trí ảnh sản phẩm không hợp lệ")
    if int(request.headers.get("content-length") or 0) > MAX_UPLOAD:
        raise HTTPException(status_code=413, detail="Ảnh quá lớn (tối đa 15 MB)")
    data = await request.body()
    if not data:
        raise HTTPException(status_code=400, detail="Chưa có dữ liệu ảnh")
    if len(data) > MAX_UPLOAD:
        raise HTTPException(status_code=413, detail="Ảnh quá lớn (tối đa 15 MB)")
    ext = _sniff_image(data)
    _staging_root().mkdir(parents=True, exist_ok=True)
    name = _replace_image(_staging_root(), f"anh_sp_{slot + 1}", ext, data)
    meta = _read_slots_meta()
    meta["overrides"][str(slot)] = name
    _write_slots_meta(meta)
    stamp = int((_staging_root() / name).stat().st_mtime)
    return {
        "slot": slot,
        "name": name,
        "url": f"/api/studio/staging-image/{name}?v={stamp}",
        "uploaded": True,
    }


@router.delete("/staging-image", dependencies=[Depends(require_studio)])
def delete_staging_image(slot: int = 0):
    _no_job_or_409()
    if not 0 <= slot < MAX_PRODUCT_IMAGES:
        raise HTTPException(status_code=400, detail="Vị trí ảnh sản phẩm không hợp lệ")
    if _staging_root().is_dir():
        for ext in IMAGE_EXTS:
            (_staging_root() / f"anh_sp_{slot + 1}{ext}").unlink(missing_ok=True)
    meta = _read_slots_meta()
    meta["overrides"][str(slot)] = ""
    _write_slots_meta(meta)
    return {"slot": slot, "deleted": True}


@router.get("/staging-image/{name}")
def get_staging_image(name: str):
    if not STAGING_FILE.match(name) or not (_staging_root() / name).is_file():
        raise HTTPException(status_code=404, detail="Không có ảnh này")
    return FileResponse(_staging_root() / name, headers={"Cache-Control": "no-store"})


def _normalize_create_images(req_images: Optional[List[str]], base_images: List[str]) -> Optional[List[str]]:
    if req_images is not None:
        cleaned = []
        for raw in req_images[:MAX_PRODUCT_IMAGES]:
            item = str(raw or "").strip()
            if not item:
                continue
            if item.startswith("/api/studio/staging-image/"):
                item = item.split("/api/studio/staging-image/", 1)[1].split("?", 1)[0]
            if STAGING_FILE.match(item):
                if not (_staging_root() / item).is_file():
                    raise HTTPException(status_code=400, detail=f"Ảnh tải lên ({item}) không tồn tại, hãy tải lại ảnh")
                cleaned.append(item)
            elif item.startswith(("http://", "https://")):
                cleaned.append(item)
            else:
                raise HTTPException(status_code=400, detail="Nguồn ảnh sản phẩm không hợp lệ")
        return cleaned

    meta = _read_slots_meta()
    preview_imgs = meta["preview"] or base_images
    overrides = meta["overrides"]
    has_disk_staging = any(
        (_staging_root() / f"anh_sp_{k + 1}{ext}").is_file()
        for k in range(MAX_PRODUCT_IMAGES)
        for ext in IMAGE_EXTS
    )
    if not overrides and not has_disk_staging and not preview_imgs:
        return None
    slots = [preview_imgs[k] if k < len(preview_imgs) else None for k in range(MAX_PRODUCT_IMAGES)]
    for k in range(MAX_PRODUCT_IMAGES):
        key = str(k)
        if key in overrides:
            val = overrides[key]
            slots[k] = val if (val and (_staging_root() / val).is_file()) else None
        else:
            for ext in IMAGE_EXTS:
                cand = f"anh_sp_{k + 1}{ext}"
                if (_staging_root() / cand).is_file():
                    slots[k] = cand
                    break
    return [s for s in slots if s]


@router.post("/create", dependencies=[Depends(require_studio)])
def create_video(req: CreateVideoRequest):
    import product_sources

    _no_job_or_409()
    if req.style not in ("story", "simple"):
        raise HTTPException(status_code=400, detail="Kiểu video phải là story hoặc simple")
    _validate_price(req.price)

    url = (req.product_url or "").strip()
    name = (req.name or "").strip()
    sheet_row = req.sheet_row
    if sheet_row is None and not url and not name:
        raise HTTPException(
            status_code=400,
            detail="Hãy dán link sản phẩm TikTok Shop hoặc chọn dòng trên Google Sheet.",
        )

    base_images: List[str] = []
    csv_path_used = ""
    sheet_ref = (os.environ.get("SPREADSHEET_ID") or settings.SPREADSHEET_ID or "").strip()

    if sheet_row is not None:
        if sheet_row == 1:
            raise HTTPException(
                status_code=400,
                detail="Dòng 1 là dòng tiêu đề cột. Hãy chọn từ dòng số 2 trở đi.",
            )
        if sheet_row < 1:
            raise HTTPException(
                status_code=400,
                detail="Số dòng không hợp lệ. Hãy chọn từ dòng số 2 trở đi.",
            )
        sheet = _open_sheet(req.tab)
        csv_path_used = str(getattr(sheet, "path", "") or "")
        row = sheet.get_row(sheet_row)
        if not row or (
            not (row.get("name") or "").strip()
            and not (row.get("product_url") or "").strip()
            and not name
            and not url
        ):
            raise HTTPException(
                status_code=400,
                detail=f"Dòng {sheet_row} đang trống hoặc không có sản phẩm. Hãy chọn dòng khác.",
            )
        base_images = [x.strip() for x in (row.get("images") or "").split("|") if x.strip()][:MAX_PRODUCT_IMAGES]
        row_name = (row.get("name") or "").strip()
        row_url = url or (row.get("product_url") or "").strip()
        if not name and not row_name:
            if row_url:
                try:
                    info = product_sources.fetch_tiktok_product(row_url)
                    name = (info.get("title") or "").strip()
                    if not base_images and info.get("images"):
                        base_images = list(info["images"][:MAX_PRODUCT_IMAGES])
                except Exception:
                    pass
            if not name:
                raise HTTPException(
                    status_code=400,
                    detail="TikTok tạm chặn đọc tự động từ link này. Bạn hãy tự nhập Tên sản phẩm rồi bấm Tạo video.",
                )
    else:
        if url and (not name or req.price is None or req.images is None):
            try:
                info = product_sources.fetch_tiktok_product(url)
                if not name and info.get("title"):
                    name = info["title"].strip()
                if req.price is None and info.get("price"):
                    req.price = int(info["price"])
                if info.get("images"):
                    base_images = list(info["images"][:MAX_PRODUCT_IMAGES])
            except Exception:
                if not name:
                    raise HTTPException(
                        status_code=400,
                        detail="TikTok tạm chặn đọc tự động từ link này. Bạn hãy tự nhập Tên sản phẩm rồi bấm Tạo video.",
                    )
        if not name:
            raise HTTPException(status_code=400, detail="Hãy nhập Tên sản phẩm trước khi bấm Tạo video.")

    final_images = _normalize_create_images(req.images, base_images)
    points = [
        p.strip().lstrip("-• ").strip()
        for p in re.split(r"[\n|]+", req.selling_points or "")
        if p.strip()
    ]
    spec = {
        "sheet_row": sheet_row,
        "sheet_ref": sheet_ref,
        "csv_path": csv_path_used,
        "tab": req.tab,
        "product_url": url or None,
        "name": name or None,
        "price": req.price,
        "images": final_images,
        "style": req.style,
        "category": (req.category or "").strip() or None,
        "selling_points": points or None,
        "notes": (req.notes or "").strip() or None,
        "output_dir": str(_videos_root()),
    }
    return _start_create_job(spec)
