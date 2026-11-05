"""
Telegram Notification helper.
"""
import logging
import requests
from app.core.config import settings

logger = logging.getLogger(__name__)


def send_telegram(message: str, parse_mode: str = "Markdown") -> bool:
    """
    Gửi message qua Telegram Bot API.
    Returns True nếu thành công.
    """
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        logger.debug("Telegram not configured — skipping notification")
        return False

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": settings.TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
        response.raise_for_status()
        return True
    except Exception as e:
        logger.warning(f"Telegram send failed: {e}")
        return False
