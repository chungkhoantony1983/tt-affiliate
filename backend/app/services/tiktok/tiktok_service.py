"""
TikTok API Service - upload và quản lý video
Sử dụng TikTok Content Posting API v2
"""
import httpx
from app.core.config import settings


TIKTOK_API_BASE = "https://open.tiktokapis.com/v2"


class TikTokService:
    def __init__(self):
        self.client_key = settings.TIKTOK_CLIENT_KEY
        self.client_secret = settings.TIKTOK_CLIENT_SECRET
        self.access_token = settings.TIKTOK_ACCESS_TOKEN

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    async def initialize_upload(self, video_size: int) -> dict:
        """
        Bước 1: Khởi tạo upload session với TikTok.
        Returns: {publish_id, upload_url}
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{TIKTOK_API_BASE}/post/publish/inbox/video/init/",
                headers=self._headers(),
                json={
                    "source_info": {
                        "source": "FILE_UPLOAD",
                        "video_size": video_size,
                        "chunk_size": video_size,
                        "total_chunk_count": 1
                    }
                }
            )
            response.raise_for_status()
            return response.json()["data"]

    async def upload_video_chunk(self, upload_url: str, video_path: str) -> bool:
        """
        Bước 2: Upload file video lên TikTok.
        """
        with open(video_path, "rb") as f:
            video_data = f.read()

        video_size = len(video_data)

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.put(
                upload_url,
                content=video_data,
                headers={
                    "Content-Type": "video/mp4",
                    "Content-Range": f"bytes 0-{video_size - 1}/{video_size}",
                    "Content-Length": str(video_size)
                }
            )
            return response.status_code in (200, 201)

    async def publish_video(
        self,
        video_path: str,
        caption: str,
        hashtags: list[str],
        privacy_level: str = "PUBLIC_TO_EVERYONE"
    ) -> dict:
        """
        Upload và publish video lên TikTok.
        
        Args:
            video_path: đường dẫn file video local
            caption: caption cho video
            hashtags: list hashtag (không có #)
            privacy_level: PUBLIC_TO_EVERYONE / MUTUAL_FOLLOW_FRIENDS / SELF_ONLY
        
        Returns: {tiktok_video_id, share_url}
        """
        import os
        video_size = os.path.getsize(video_path)

        # Bước 1: Khởi tạo upload
        init_data = await self.initialize_upload(video_size)
        publish_id = init_data["publish_id"]
        upload_url = init_data["upload_url"]

        # Bước 2: Upload video
        success = await self.upload_video_chunk(upload_url, video_path)
        if not success:
            raise Exception("Failed to upload video chunk to TikTok")

        # Bước 3: Lấy trạng thái publish
        status_data = await self.check_publish_status(publish_id)

        return {
            "publish_id": publish_id,
            "status": status_data.get("status")
        }

    async def check_publish_status(self, publish_id: str) -> dict:
        """Kiểm tra trạng thái upload/publish."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{TIKTOK_API_BASE}/post/publish/status/fetch/",
                headers=self._headers(),
                json={"publish_id": publish_id}
            )
            response.raise_for_status()
            return response.json()["data"]

    async def get_video_stats(self, video_ids: list[str]) -> list[dict]:
        """Lấy thống kê performance của các video."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{TIKTOK_API_BASE}/video/query/",
                headers=self._headers(),
                params={
                    "fields": "id,title,view_count,like_count,comment_count,share_count"
                },
                json={"filters": {"video_ids": video_ids}}
            )
            response.raise_for_status()
            return response.json()["data"]["videos"]
