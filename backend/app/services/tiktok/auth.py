"""
TikTok OAuth2 Token Management.

Flow:
  1. Redirect user → TikTok OAuth page
  2. TikTok redirect về callback URL với `code`
  3. Exchange `code` → access_token + refresh_token
  4. Store tokens (DB hoặc .env)
  5. Auto-refresh khi gần hết hạn

Docs: https://developers.tiktok.com/doc/oauth-user-access-token-management
"""
import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple

import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

TIKTOK_OAUTH_BASE = "https://www.tiktok.com/v2/auth/authorize/"
TIKTOK_TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
TIKTOK_REVOKE_URL = "https://open.tiktokapis.com/v2/oauth/revoke/"
TIKTOK_USER_INFO_URL = "https://open.tiktokapis.com/v2/user/info/"

# Scopes cần thiết cho affiliate bot — chỉ Upload (inbox draft), không Direct Post.
# Chỉ xin đúng scope đang dùng để app review dễ được duyệt.
REQUIRED_SCOPES = [
    "user.info.basic",
    "video.upload",
]


class TikTokAuth:
    """
    Quản lý OAuth2 token lifecycle cho TikTok Content Posting API.
    """

    def __init__(self):
        self.client_key = settings.TIKTOK_CLIENT_KEY
        self.client_secret = settings.TIKTOK_CLIENT_SECRET

    def get_auth_url(self, redirect_uri: str, state: str = None) -> Tuple[str, str]:
        """
        Tạo Authorization URL để redirect user đến TikTok OAuth.

        Returns: (auth_url, code_verifier) — lưu code_verifier để dùng khi exchange
        """
        code_verifier = secrets.token_urlsafe(64)
        code_challenge = hashlib.sha256(code_verifier.encode()).digest().hex()

        if not state:
            state = secrets.token_urlsafe(16)

        params = {
            "client_key": self.client_key,
            "scope": ",".join(REQUIRED_SCOPES),
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }

        from urllib.parse import urlencode
        auth_url = f"{TIKTOK_OAUTH_BASE}?{urlencode(params)}"
        return auth_url, code_verifier

    def get_web_auth_url(self, redirect_uri: str, state: str) -> str:
        """Authorization URL cho Login Kit Web (không dùng PKCE)."""
        from urllib.parse import urlencode
        params = {
            "client_key": self.client_key,
            "scope": ",".join(REQUIRED_SCOPES),
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "state": state,
        }
        return f"{TIKTOK_OAUTH_BASE}?{urlencode(params)}"

    async def get_user_info(self, access_token: str) -> dict:
        """Lấy display name + avatar của tài khoản vừa kết nối."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                TIKTOK_USER_INFO_URL,
                params={"fields": "open_id,avatar_url,display_name"},
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            user = response.json().get("data", {}).get("user", {})
            return {
                "display_name": user.get("display_name", ""),
                "avatar_url": user.get("avatar_url", ""),
            }

    async def revoke(self, access_token: str) -> None:
        """Thu hồi quyền app với tài khoản TikTok."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                TIKTOK_REVOKE_URL,
                data={
                    "client_key": self.client_key,
                    "client_secret": self.client_secret,
                    "token": access_token,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()

    async def exchange_code(
        self, code: str, redirect_uri: str, code_verifier: Optional[str] = None
    ) -> dict:
        """
        Exchange authorization code → access_token + refresh_token.

        Returns: {access_token, refresh_token, expires_in, open_id}
        """
        form = {
            "client_key": self.client_key,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }
        if code_verifier:
            form["code_verifier"] = code_verifier

        async with httpx.AsyncClient() as client:
            response = await client.post(
                TIKTOK_TOKEN_URL,
                data=form,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            data = response.json()

            if data.get("error"):
                raise ValueError(f"TikTok OAuth error: {data.get('error_description', data['error'])}")

            return {
                "access_token": data["access_token"],
                "refresh_token": data["refresh_token"],
                "expires_in": data.get("expires_in", 86400),
                "refresh_expires_in": data.get("refresh_expires_in", 2592000),
                "open_id": data.get("open_id", ""),
                "scope": data.get("scope", ""),
            }

    async def refresh_access_token(self, refresh_token: str) -> dict:
        """
        Refresh access token khi hết hạn.

        TikTok access token có thời hạn 24h, refresh token 60 ngày.
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                TIKTOK_TOKEN_URL,
                data={
                    "client_key": self.client_key,
                    "client_secret": self.client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            data = response.json()

            if data.get("error"):
                raise ValueError(f"TikTok token refresh error: {data.get('error_description')}")

            logger.info("TikTok access token refreshed successfully")
            return {
                "access_token": data["access_token"],
                "refresh_token": data.get("refresh_token", refresh_token),
                "expires_in": data.get("expires_in", 86400),
            }

    async def get_valid_token(self) -> str:
        """
        Lấy access token hợp lệ, tự động refresh nếu cần.
        Fallback về settings.TIKTOK_ACCESS_TOKEN nếu không có refresh flow.
        """
        # Simple implementation: dùng token từ .env
        # Production: check DB, refresh nếu expires_at < now + 1h
        token = settings.TIKTOK_ACCESS_TOKEN
        if not token:
            raise ValueError(
                "No TikTok access token configured. "
                "Run OAuth flow at /api/tiktok/auth/login"
            )
        return token
