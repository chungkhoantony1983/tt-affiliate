"""
Creator API — local endpoints behind app.html on GitHub Pages.

Flow:
  1. GET  /api/creator/auth/url       — build the Login with TikTok URL
  2. POST /api/creator/auth/exchange  — exchange `code` for tokens (kept in memory)
  3. GET  /api/creator/videos         — list rendered videos in storage/videos
  4. POST /api/creator/videos/{folder}/send — upload a video to the creator's inbox
"""
import json
import logging
import secrets
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.core.config import settings
from app.services.tiktok.auth import TikTokAuth
from app.services.tiktok.tiktok_service import TikTokService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/creator", tags=["creator"])

# In-memory only: tokens disappear when the local service stops.
_session: dict = {}
_pending_states: set = set()


class ExchangeRequest(BaseModel):
    code: str
    state: str


def _videos_root() -> Path:
    return Path(settings.STORAGE_PATH) / "videos"


def _video_folders() -> List[Path]:
    root = _videos_root()
    if not root.is_dir():
        return []
    folders = [p for p in root.iterdir() if (p / "video.mp4").is_file()]
    return sorted(folders, key=lambda p: p.name, reverse=True)


def _folder_or_404(name: str) -> Path:
    for folder in _video_folders():
        if folder.name == name:
            return folder
    raise HTTPException(status_code=404, detail="Video not found")


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _access_token() -> str:
    token = _session.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Connect your TikTok account first")
    return token


def _require_app_keys() -> None:
    if not settings.TIKTOK_CLIENT_KEY or not settings.TIKTOK_CLIENT_SECRET:
        raise HTTPException(
            status_code=503,
            detail="TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET are missing from .env",
        )


@router.get("/auth/url")
def auth_url():
    _require_app_keys()
    state = secrets.token_urlsafe(16)
    _pending_states.add(state)
    return {"auth_url": TikTokAuth().get_web_auth_url(settings.TIKTOK_REDIRECT_URI, state)}


@router.post("/auth/exchange")
async def auth_exchange(req: ExchangeRequest):
    if req.state not in _pending_states:
        raise HTTPException(status_code=400, detail="Login expired, please try again")
    _pending_states.discard(req.state)

    auth = TikTokAuth()
    try:
        tokens = await auth.exchange_code(req.code, settings.TIKTOK_REDIRECT_URI)
        profile = await auth.get_user_info(tokens["access_token"])
    except Exception as e:
        logger.error(f"TikTok login failed: {e}")
        raise HTTPException(status_code=502, detail=str(e))

    _session.update(access_token=tokens["access_token"], profile=profile)
    return {"connected": True, **profile}


@router.get("/me")
def me():
    if not _session.get("access_token"):
        return {"connected": False}
    return {"connected": True, **_session.get("profile", {})}


@router.post("/disconnect")
async def disconnect():
    token: Optional[str] = _session.get("access_token")
    _session.clear()
    if token:
        await TikTokAuth().revoke(token)
    return {"connected": False}


@router.get("/videos")
def list_videos():
    items = []
    for folder in _video_folders():
        product = _read_json(folder / "product.json")
        script = _read_json(folder / "script.json")
        hashtags = " ".join(script.get("hashtags") or [])
        items.append({
            "folder": folder.name,
            "title": product.get("name") or folder.name,
            "caption": f"{script.get('caption', '')} {hashtags}".strip(),
        })
    return {"videos": items}


@router.get("/videos/{folder}/file")
def video_file(folder: str):
    return FileResponse(_folder_or_404(folder) / "video.mp4", media_type="video/mp4")


@router.post("/videos/{folder}/send")
async def send_video(folder: str):
    token = _access_token()
    path = _folder_or_404(folder) / "video.mp4"
    try:
        return await TikTokService(access_token=token).upload_draft(str(path))
    except Exception as e:
        logger.error(f"Inbox upload failed: {e}")
        raise HTTPException(status_code=502, detail=str(e))
