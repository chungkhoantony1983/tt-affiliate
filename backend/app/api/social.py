"""
Social Publishing API endpoints:
  POST /api/social/publish/{job_id}     — trigger publish video job lên social
  GET  /api/social/publish/{job_id}/status — check publish status
  GET  /api/tiktok/auth/login           — TikTok OAuth login
  GET  /api/tiktok/auth/callback        — OAuth callback
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import VideoJob, VideoStatus
from app.services.tiktok.tiktok_service import TikTokService
from app.services.tiktok.auth import TikTokAuth

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["social"])

# Temp storage cho OAuth code_verifier (production: dùng Redis/session)
_oauth_store: dict = {}


@router.get("/tiktok/auth/login")
async def tiktok_login(
    redirect_uri: str = Query(..., description="Your app callback URL"),
):
    """
    Bước 1: Redirect user đến TikTok OAuth page.
    Response trả về auth_url để frontend redirect.
    """
    auth = TikTokAuth()
    auth_url, code_verifier = auth.get_auth_url(redirect_uri)

    # Store code_verifier (in production: use Redis with expiry)
    import hashlib
    verifier_key = hashlib.md5(redirect_uri.encode()).hexdigest()
    _oauth_store[verifier_key] = code_verifier

    return {
        "auth_url": auth_url,
        "message": "Redirect user to auth_url to authorize TikTok access",
    }


@router.get("/tiktok/auth/callback")
async def tiktok_callback(
    code: str = Query(...),
    state: str = Query(None),
    redirect_uri: str = Query(...),
):
    """
    Bước 2: TikTok gọi về đây với `code` sau khi user authorize.
    Exchange code → access_token.
    """
    import hashlib
    verifier_key = hashlib.md5(redirect_uri.encode()).hexdigest()
    code_verifier = _oauth_store.pop(verifier_key, None)

    if not code_verifier:
        raise HTTPException(
            status_code=400,
            detail="OAuth state not found. Please restart the login flow.",
        )

    auth = TikTokAuth()
    try:
        tokens = await auth.exchange_code(code, redirect_uri, code_verifier)
        # Production: lưu tokens vào DB (social_auth table), encrypt at rest
        logger.info(f"TikTok OAuth success: open_id={tokens.get('open_id')}")
        return {
            "message": "TikTok authorized successfully",
            "open_id": tokens.get("open_id"),
            "scope": tokens.get("scope"),
            "note": "Store access_token and refresh_token in .env or DB",
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "expires_in": tokens["expires_in"],
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/social/publish/{job_id}")
async def publish_video(
    job_id: int,
    platform: str = Query("tiktok", description="Target platform: tiktok"),
    db: Session = Depends(get_db),
):
    """
    Trigger publish video job lên social platform.
    Job phải ở trạng thái 'rendered'.
    """
    job = db.query(VideoJob).filter(VideoJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Video job not found")

    if job.status != VideoStatus.RENDERED:
        raise HTTPException(
            status_code=400,
            detail=f"Job must be in 'rendered' status, current: {job.status}",
        )

    if not job.video_path:
        raise HTTPException(status_code=400, detail="No video file attached to job")

    # Dispatch to background task
    import json
    from app.tasks.sync_task import upload_video_task
    upload_video_task.delay(job_id, platform)

    return {
        "message": f"Video publish triggered for job {job_id} → {platform}",
        "job_id": job_id,
        "platform": platform,
        "status": "uploading",
    }


@router.get("/social/publish/{job_id}/status")
def get_publish_status(job_id: int, db: Session = Depends(get_db)):
    """Check trạng thái publish của video job."""
    job = db.query(VideoJob).filter(VideoJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Video job not found")

    return {
        "job_id": job_id,
        "status": job.status,
        "platform": job.social_platform,
        "platform_video_id": job.platform_video_id,
        "share_url": job.share_url,
        "publish_time": job.publish_time.isoformat() if job.publish_time else None,
        "error_message": job.error_message,
    }
