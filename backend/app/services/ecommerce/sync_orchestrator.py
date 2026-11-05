"""
SyncOrchestrator — Orchestrate multi-platform e-commerce product sync.

Flow:
  1. Iterate over enabled adapters (Shopee, Lazada, ...)
  2. Fetch products từ mỗi platform
  3. Upsert vào DB theo (source_platform, source_item_id)
  4. Flag hot products (is_priority)
  5. Deactivate products không còn được trả về
  6. Send Telegram notification
"""
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from app.models.models import Product
from app.services.ecommerce.adapters.base import ProductData, EcommerceAdapter
from app.services.ecommerce.adapters.shopee import ShopeeAdapter
from app.services.ecommerce.product_ranker import ProductRanker

logger = logging.getLogger(__name__)


def _get_enabled_adapters() -> List[EcommerceAdapter]:
    """Return danh sách adapters đã được configure."""
    adapters = []

    shopee = ShopeeAdapter()
    if shopee.is_configured():
        adapters.append(shopee)

    try:
        from app.services.ecommerce.adapters.lazada import LazadaAdapter
        lazada = LazadaAdapter()
        if lazada.is_configured():
            adapters.append(lazada)
    except Exception:
        pass  # Lazada not configured

    return adapters


class SyncOrchestrator:
    """
    Orchestrate việc sync product từ nhiều e-commerce platforms.
    Tuân theo L3 ecommerce-sync capability design.
    """

    def __init__(self, db: Session):
        self.db = db
        self.ranker = ProductRanker()

    def run(self) -> Dict:
        """
        Chạy full sync cycle cho tất cả enabled platforms.
        Returns stats dict: {platform: {new, updated, deactivated}}
        """
        adapters = _get_enabled_adapters()
        if not adapters:
            logger.warning("No e-commerce adapters configured!")
            return {"error": "No adapters configured"}

        total_stats = {}
        for adapter in adapters:
            try:
                stats = self._sync_platform(adapter)
                total_stats[adapter.platform_name] = stats
                logger.info(f"[{adapter.platform_name}] Sync done: {stats}")
            except Exception as e:
                logger.error(f"[{adapter.platform_name}] Sync failed: {e}", exc_info=True)
                total_stats[adapter.platform_name] = {"error": str(e)}

        # Notify via Telegram
        self._send_notification(total_stats)
        return total_stats

    def _sync_platform(self, adapter: EcommerceAdapter) -> Dict:
        """Sync một platform. Returns {new, updated, deactivated, total}."""
        platform = adapter.platform_name
        logger.info(f"[{platform}] Starting product fetch...")

        # Fetch từ API
        products_data: List[ProductData] = adapter.fetch_products(limit=500)
        if not products_data:
            logger.warning(f"[{platform}] No products returned from API")
            return {"new": 0, "updated": 0, "deactivated": 0, "total": 0}

        # Generate affiliate links
        products_data = adapter.refresh_affiliate_links(products_data)

        # Upsert vào DB
        fetched_ids = set()
        new_count = 0
        updated_count = 0

        for p_data in products_data:
            fetched_ids.add(p_data.source_item_id)
            is_new = self._upsert_product(p_data)
            if is_new:
                new_count += 1
            else:
                updated_count += 1

        # Deactivate sản phẩm không còn trong list
        deactivated = self._deactivate_missing(platform, fetched_ids)

        # Flag hot products
        self._flag_hot_products(platform)

        self.db.commit()
        return {
            "new": new_count,
            "updated": updated_count,
            "deactivated": deactivated,
            "total": len(products_data),
        }

    def _upsert_product(self, p: ProductData) -> bool:
        """
        Upsert product theo (source_platform, source_item_id).
        Returns True nếu là sản phẩm mới.
        """
        existing = (
            self.db.query(Product)
            .filter(
                Product.source_platform == p.source_platform,
                Product.source_item_id == p.source_item_id,
            )
            .first()
        )

        if existing:
            # Update existing
            existing.name = p.name
            existing.price = p.price
            existing.original_price = p.original_price
            existing.discount_percent = p.discount_percent
            existing.description = p.description
            existing.category = p.category
            existing.image_urls = json.dumps(p.image_urls, ensure_ascii=False)
            existing.source_url = p.source_url
            existing.stock = p.stock
            existing.sales_count = p.sales_count
            existing.rating = p.rating
            existing.is_active = p.is_active
            if p.affiliate_link:
                existing.affiliate_link = p.affiliate_link
            existing.last_synced = datetime.utcnow()
            return False
        else:
            # Insert new
            product = Product(
                source_platform=p.source_platform,
                source_item_id=p.source_item_id,
                name=p.name,
                price=p.price,
                original_price=p.original_price,
                discount_percent=p.discount_percent,
                description=p.description,
                category=p.category,
                image_urls=json.dumps(p.image_urls, ensure_ascii=False),
                source_url=p.source_url,
                affiliate_link=p.affiliate_link,
                stock=p.stock,
                sales_count=p.sales_count,
                rating=p.rating,
                is_active=p.is_active,
                last_synced=datetime.utcnow(),
            )
            self.db.add(product)
            return True

    def _deactivate_missing(self, platform: str, fetched_ids: set) -> int:
        """Đánh dấu is_active=False cho sản phẩm không còn trong API response."""
        active_products = (
            self.db.query(Product)
            .filter(Product.source_platform == platform, Product.is_active == True)
            .all()
        )
        count = 0
        for product in active_products:
            if product.source_item_id not in fetched_ids:
                product.is_active = False
                count += 1
        return count

    def _flag_hot_products(self, platform: str):
        """
        Flag is_priority cho hot products:
        - Discount > 20%
        - Sales count trong top 20%
        """
        products = (
            self.db.query(Product)
            .filter(Product.source_platform == platform, Product.is_active == True)
            .all()
        )

        if not products:
            return

        # Top 20% sales threshold
        sales_counts = sorted([p.sales_count for p in products], reverse=True)
        top_threshold = sales_counts[max(0, len(sales_counts) // 5 - 1)]

        for product in products:
            is_hot = (
                (product.discount_percent or 0) >= 20
                or product.sales_count >= top_threshold
            )
            product.is_priority = is_hot

    def _send_notification(self, stats: Dict):
        """Gửi sync summary qua Telegram."""
        try:
            from app.services.notification import send_telegram
            lines = ["✅ *E-commerce Sync Complete*"]
            for platform, s in stats.items():
                if "error" in s:
                    lines.append(f"❌ *{platform.capitalize()}*: {s['error']}")
                else:
                    lines.append(
                        f"📦 *{platform.capitalize()}*: "
                        f"+{s['new']} new | {s['updated']} updated | "
                        f"{s['deactivated']} deactivated"
                    )
            send_telegram("\n".join(lines))
        except Exception as e:
            logger.warning(f"Telegram notification failed: {e}")
