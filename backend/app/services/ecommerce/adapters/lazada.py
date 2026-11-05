"""
LazadaAdapter — Placeholder implementation cho Lazada Open Platform.
Implement đầy đủ khi LAZADA_APP_KEY được cấu hình.
"""
import logging
from typing import List
from .base import EcommerceAdapter, ProductData
from app.core.config import settings

logger = logging.getLogger(__name__)


class LazadaAdapter(EcommerceAdapter):
    """Lazada Open Platform adapter (future implementation)."""

    def __init__(self):
        self.app_key = settings.LAZADA_APP_KEY
        self.app_secret = settings.LAZADA_APP_SECRET

    @property
    def platform_name(self) -> str:
        return "lazada"

    def is_configured(self) -> bool:
        return bool(self.app_key and self.app_secret)

    def fetch_products(self, limit: int = 200) -> List[ProductData]:
        if not self.is_configured():
            logger.info("Lazada not configured — skipping")
            return []
        # TODO: Implement Lazada API calls
        raise NotImplementedError("LazadaAdapter.fetch_products not yet implemented")

    def generate_affiliate_link(self, item_id: str) -> str:
        raise NotImplementedError("LazadaAdapter.generate_affiliate_link not yet implemented")
