"""
Celery sync tasks — Background tasks cho e-commerce sync và social publish.
"""
import asyncio
import json
import logging
from datetime import datetime
from celery import Celery
from celery.utils.log import get_task_logger

from app.core.config import settings

logger = get_task_logger(__name__)

celery_app = Celery(
    "affiliate_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"


@celery_app.task(bind=True, name="tasks.sync_ecommerce", max_retries=2)
def sync_ecommerce_task(self):
    """
    Celery task: sync tất cả e-commerce platforms.
    Được trigger từ N8N scheduler hoặc /api/ecommerce/sync.
    """
    from app.core.database import SessionLocal
    from app.services.ecommerce.sync_orchestrator import SyncOrchestrator

    db = SessionLocal()
    try:
        logger.info("Starting e-commerce sync task...")
        orchestrator = SyncOrchestrator(db)
        result = orchestrator.run()
        logger.info(f"E-commerce sync completed: {result}")
        return result
    except Exception as exc:
        logger.error(f"E-commerce sync task failed: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=300)   # Retry sau 5 phút
    finally:
        db.close()


@celery_app.task(bind=True, name="tasks.upload_video", max_retries=3)
def upload_video_task(self, job_id: int, platform: str = "tiktok"):
    """
    Celery task: upload video đã render lên social platform.
    """
    from app.core.database import SessionLocal
    from app.models.models import VideoJob, VideoStatus

    db = SessionLocal()
    job = None

    try:
        job = db.query(VideoJob).filter(VideoJob.id == job_id).first()
        if not job:
            logger.error(f"VideoJob {job_id} not found")
            return

        if job.status != VideoStatus.RENDERED:
            logger.warning(f"Job {job_id} not in RENDERED state: {job.status}")
            return

        job.status = VideoStatus.UPLOADING
        db.commit()

        caption = job.caption or ""
        hashtags = json.loads(job.hashtags or "[]")
        full_caption = caption + " " + " ".join(f"#{h}" for h in hashtags)

        if platform == "tiktok":
            from app.services.tiktok.tiktok_service import TikTokService
            tiktok = TikTokService()
            # Upload vào inbox — creator tự dán caption và bấm đăng trong app TikTok
            result = asyncio.get_event_loop().run_until_complete(
                tiktok.upload_draft(video_path=job.video_path)
            )
            logger.info(f"[Job {job_id}] Caption to paste in TikTok app: {full_caption}")
            job.platform_video_id = result.get("publish_id")
            job.social_platform = "tiktok"
        else:
            raise NotImplementedError(f"Platform {platform} not yet supported")

        job.status = VideoStatus.PUBLISHED
        job.publish_time = datetime.utcnow()
        db.commit()

        logger.info(f"[Job {job_id}] Published to {platform}: {result}")
        return {"job_id": job_id, "platform": platform, "status": "published"}

    except Exception as exc:
        logger.error(f"[Job {job_id}] Upload failed: {exc}", exc_info=True)
        if job:
            job.status = VideoStatus.FAILED
            job.error_message = str(exc)
            db.commit()
        raise self.retry(exc=exc, countdown=60)
    finally:
        db.close()
