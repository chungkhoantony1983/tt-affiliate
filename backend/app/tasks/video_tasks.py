"""
Celery Tasks - xử lý video generation pipeline bất đồng bộ
"""
from celery import Celery
from celery.utils.log import get_task_logger
import os
import json
import requests
from pathlib import Path

from app.core.config import settings
from app.services.ai.script_generator import generate_product_script, generate_voiceover
from app.services.video.renderer import render_product_video, download_image
from app.services.tiktok.tiktok_service import TikTokService

logger = get_task_logger(__name__)

celery_app = Celery(
    "affiliate_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)


@celery_app.task(bind=True, max_retries=3, name="tasks.generate_product_video")
def generate_product_video(self, job_id: int, product_data: dict):
    """
    Pipeline chính: từ product data → video TikTok hoàn chỉnh
    
    Stages:
    1. Generate script (AI)
    2. Generate voiceover (TTS)
    3. Download product images
    4. Render video (FFmpeg)
    5. Update job status
    """
    import asyncio
    from app.core.database import SessionLocal
    from app.models.models import VideoJob, VideoStatus

    db = SessionLocal()

    try:
        job = db.query(VideoJob).filter(VideoJob.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        storage_dir = Path(settings.STORAGE_PATH) / str(job_id)
        storage_dir.mkdir(parents=True, exist_ok=True)

        # Stage 1: Generate script
        logger.info(f"[Job {job_id}] Generating script...")
        job.status = VideoStatus.SCRIPT_GENERATED
        db.commit()

        script = asyncio.get_event_loop().run_until_complete(
            generate_product_script(product_data)
        )
        job.script = json.dumps(script, ensure_ascii=False)
        job.hook_text = script.get("hook", "")
        job.hashtags = json.dumps(script.get("hashtags", []), ensure_ascii=False)
        job.caption = script.get("caption", "")
        db.commit()

        # Stage 2: Generate voiceover
        logger.info(f"[Job {job_id}] Generating voiceover...")
        audio_path = str(storage_dir / "voiceover.mp3")
        asyncio.get_event_loop().run_until_complete(
            generate_voiceover(script["voiceover_text"], audio_path)
        )
        job.audio_path = audio_path
        db.commit()

        # Stage 3: Download product images
        logger.info(f"[Job {job_id}] Downloading product images...")
        image_urls = json.loads(product_data.get("image_urls", "[]"))[:4]  # max 4 ảnh
        local_images = []

        for i, url in enumerate(image_urls):
            img_path = str(storage_dir / f"product_{i}.jpg")
            try:
                download_image(url, img_path)
                local_images.append(img_path)
            except Exception as e:
                logger.warning(f"Failed to download image {url}: {e}")

        if not local_images:
            raise Exception("No product images available")

        # Stage 4: Render video
        logger.info(f"[Job {job_id}] Rendering video...")
        job.status = VideoStatus.RENDERING
        db.commit()

        video_path = str(storage_dir / "output.mp4")
        render_product_video(
            product=product_data,
            script=script,
            image_paths=local_images,
            audio_path=audio_path,
            output_path=video_path
        )

        job.video_path = video_path
        job.status = VideoStatus.RENDERED
        db.commit()

        logger.info(f"[Job {job_id}] Video rendered successfully: {video_path}")
        return {"job_id": job_id, "video_path": video_path, "status": "rendered"}

    except Exception as exc:
        logger.error(f"[Job {job_id}] Failed: {exc}")
        if job:
            from app.models.models import VideoStatus
            job.status = VideoStatus.FAILED
            job.error_message = str(exc)
            db.commit()
        raise self.retry(exc=exc, countdown=60)

    finally:
        db.close()


@celery_app.task(name="tasks.upload_video_to_tiktok")
def upload_video_to_tiktok(job_id: int):
    """Upload video đã render lên TikTok."""
    import asyncio
    from app.core.database import SessionLocal
    from app.models.models import VideoJob, VideoStatus

    db = SessionLocal()

    try:
        job = db.query(VideoJob).filter(VideoJob.id == job_id).first()
        if not job or job.status != VideoStatus.RENDERED:
            logger.error(f"Job {job_id} not ready for upload")
            return

        job.status = VideoStatus.UPLOADING
        db.commit()

        caption = job.caption or ""
        hashtags = json.loads(job.hashtags or "[]")
        full_caption = caption + " " + " ".join(f"#{h}" for h in hashtags)

        tiktok = TikTokService()
        result = asyncio.get_event_loop().run_until_complete(
            tiktok.publish_video(
                video_path=job.video_path,
                caption=full_caption,
                hashtags=hashtags
            )
        )

        job.tiktok_video_id = result.get("publish_id")
        job.status = VideoStatus.PUBLISHED
        db.commit()

        logger.info(f"[Job {job_id}] Published to TikTok: {result}")
        return result

    except Exception as exc:
        logger.error(f"[Job {job_id}] Upload failed: {exc}")
        if job:
            job.status = VideoStatus.FAILED
            job.error_message = str(exc)
            db.commit()
        raise

    finally:
        db.close()
