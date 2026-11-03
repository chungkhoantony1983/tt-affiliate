"""
TikTok Content Posting Service — Upload video vào inbox (draft) của creator.

Sử dụng TikTok Content Posting API v2 — Upload (scope: video.upload):
  https://developers.tiktok.com/doc/content-posting-api-get-started-upload-content

App KHÔNG dùng Direct Post (video.publish). Video được gửi vào inbox TikTok,
creator mở app TikTok để thêm caption, chọn privacy và tự bấm đăng.

Flow:
  1. initialize_upload() — lấy upload_url + publish_id
  2. upload_video_chunk() — PUT video bytes lên upload_url
  3. check_publish_status() — poll status cho đến khi SEND_TO_USER_INBOX

Error codes: https://developers.tiktok.com/doc/content-posting-api-reference-error-codes
"""
import os
import asyncio
import logging
from typing import Optional

import httpx
from app.services.tiktok.auth import TikTokAuth

logger = logging.getLogger(__name__)

TIKTOK_API_BASE = "https://open.tiktokapis.com/v2"

# TikTok error codes
TIKTOK_ERROR_RATE_LIMIT = "too_many_requests"
TIKTOK_ERROR_INVALID_TOKEN = "access_token_invalid"
TIKTOK_ERROR_SCOPE_MISSING = "scope_not_authorized"

# Upload 1 chunk: TikTok cho phép file <= 64MB gửi nguyên 1 chunk
MAX_SINGLE_CHUNK_SIZE = 64 * 1024 * 1024


class TikTokService:
    """
    Service để upload và quản lý video trên TikTok.
    Sử dụng Content Posting API v2 với OAuth2 Bearer token.
    """

    def __init__(self):
        self.auth = TikTokAuth()

    async def _headers(self) -> dict:
        token = await self.auth.get_valid_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=UTF-8",
        }

    async def initialize_upload(self, video_size: int, video_path: str = None) -> dict:
        """
        Bước 1: Khởi tạo upload session vào inbox của creator.

        Args:
            video_size: kích thước file video (bytes)
        Returns:
            {publish_id, upload_url}
        """
        if video_size > MAX_SINGLE_CHUNK_SIZE:
            raise ValueError(
                f"Video too large for single-chunk upload: {video_size} bytes (max 64MB)"
            )

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{TIKTOK_API_BASE}/post/publish/inbox/video/init/",
                headers=await self._headers(),
                json={
                    "source_info": {
                        "source": "FILE_UPLOAD",
                        "video_size": video_size,
                        "chunk_size": video_size,
                        "total_chunk_count": 1,
                    },
                },
            )
            self._handle_error(response)
            data = response.json().get("data", {})
            logger.info(f"TikTok upload initialized: publish_id={data.get('publish_id')}")
            return data

    async def upload_video_chunk(self, upload_url: str, video_path: str) -> bool:
        """
        Bước 2: Upload video file lên TikTok pre-signed URL.

        Returns True nếu thành công.
        """
        file_size = os.path.getsize(video_path)

        with open(video_path, "rb") as f:
            video_data = f.read()

        async with httpx.AsyncClient(timeout=300) as client:  # 5 min timeout cho video lớn
            response = await client.put(
                upload_url,
                content=video_data,
                headers={
                    "Content-Type": "video/mp4",
                    "Content-Range": f"bytes 0-{file_size - 1}/{file_size}",
                    "Content-Length": str(file_size),
                },
            )
            success = response.status_code in (200, 201, 206)
            if not success:
                logger.error(f"TikTok video upload failed: {response.status_code} {response.text[:500]}")
            else:
                logger.info(f"TikTok video uploaded: {file_size} bytes")
            return success

    async def upload_draft(self, video_path: str) -> dict:
        """
        Pipeline hoàn chỉnh: upload file vào inbox TikTok của creator.

        Upload API không nhận caption/privacy — creator tự nhập trong app TikTok
        khi mở notification và bấm đăng.

        Args:
            video_path: đường dẫn file .mp4 local

        Returns:
            {publish_id, status}
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        video_size = os.path.getsize(video_path)
        logger.info(f"Uploading draft: {video_path} ({video_size / 1024 / 1024:.1f} MB)")

        # Bước 1: Init upload
        init_data = await self.initialize_upload(video_size, video_path)
        publish_id = init_data.get("publish_id")
        upload_url = init_data.get("upload_url")

        if not publish_id or not upload_url:
            raise ValueError(f"TikTok init upload returned invalid data: {init_data}")

        # Bước 2: Upload video file
        success = await self.upload_video_chunk(upload_url, video_path)
        if not success:
            raise RuntimeError("Failed to upload video to TikTok")

        # Bước 3: Poll status (TikTok xử lý async)
        status_data = await self._poll_publish_status(publish_id, max_wait_seconds=120)

        logger.info(f"TikTok draft uploaded: {publish_id} — status={status_data.get('status')}")
        return {
            "publish_id": publish_id,
            "status": status_data.get("status"),
        }

    async def _poll_publish_status(
        self, publish_id: str, max_wait_seconds: int = 120
    ) -> dict:
        """
        Poll TikTok status cho đến khi video vào inbox hoặc timeout.

        TikTok trạng thái: PROCESSING_UPLOAD → SEND_TO_USER_INBOX
        (→ PUBLISH_COMPLETE nếu creator đã tự đăng trong app)
        """
        elapsed = 0
        poll_interval = 5

        while elapsed < max_wait_seconds:
            status_data = await self.check_publish_status(publish_id)
            status = status_data.get("status", "")

            if status in ("SEND_TO_USER_INBOX", "PUBLISH_COMPLETE"):
                return status_data
            elif "FAILED" in status or "REJECTED" in status:
                fail_reason = status_data.get("fail_reason", "Unknown")
                raise RuntimeError(f"TikTok publish failed: {status} — {fail_reason}")

            logger.debug(f"TikTok publish status: {status}, waiting {poll_interval}s...")
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        logger.warning(f"TikTok publish status poll timeout after {max_wait_seconds}s")
        return {"status": "PENDING", "publish_id": publish_id}

    async def check_publish_status(self, publish_id: str) -> dict:
        """Check trạng thái upload/publish."""
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{TIKTOK_API_BASE}/post/publish/status/fetch/",
                headers=await self._headers(),
                json={"publish_id": publish_id},
            )
            self._handle_error(response)
            return response.json().get("data", {})

    def _handle_error(self, response: httpx.Response):
        """Parse TikTok error response và raise appropriate exception."""
        if response.status_code == 429:
            raise RuntimeError("TikTok API rate limit exceeded — retry after 60s")
        if response.status_code == 401:
            raise ValueError("TikTok access token invalid or expired — refresh required")
        if response.status_code >= 400:
            try:
                error_data = response.json()
                error_code = error_data.get("error", {}).get("code", "unknown")
                error_msg = error_data.get("error", {}).get("message", response.text[:200])
                raise RuntimeError(f"TikTok API error [{error_code}]: {error_msg}")
            except Exception:
                response.raise_for_status()
