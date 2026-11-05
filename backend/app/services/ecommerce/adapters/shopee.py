"""
ShopeeAdapter — Implement EcommerceAdapter cho Shopee Open Platform.

Authentication: HMAC-SHA256 signature
API: https://open.shopee.com/developer-guide/

Credentials cần thiết (.env):
  SHOPEE_APP_ID         — Partner ID từ Shopee Developer Portal
  SHOPEE_SECRET_KEY     — Partner Key (secret)
  SHOPEE_AFFILIATE_UNIQUE_ID — Unique ID cho affiliate tracking link
"""
import hashlib
import hmac
import time
import json
import logging
import requests
from typing import List, Optional
from urllib.parse import urlencode

from app.core.config import settings
from .base import EcommerceAdapter, ProductData

logger = logging.getLogger(__name__)

SHOPEE_API_BASE = "https://partner.shopeemobile.com"
SHOPEE_AFFILIATE_BASE = "https://affiliate.shopee.vn"


class ShopeeAdapter(EcommerceAdapter):
    """
    Shopee Affiliate + Open Platform adapter.

    Shopee Open Platform sử dụng HMAC-SHA256 signature cho mọi API call:
      signature = HMAC_SHA256(partner_key, path + "|" + timestamp)
    """

    def __init__(self):
        self.app_id = settings.SHOPEE_APP_ID
        self.secret_key = settings.SHOPEE_SECRET_KEY
        self.affiliate_unique_id = settings.SHOPEE_AFFILIATE_UNIQUE_ID
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "AffiliateBot/1.0"
        })

    @property
    def platform_name(self) -> str:
        return "shopee"

    def is_configured(self) -> bool:
        return bool(self.app_id and self.secret_key)

    def _sign(self, path: str, timestamp: int) -> str:
        """
        Tạo HMAC-SHA256 signature theo Shopee Open Platform spec.
        base_string = partner_id + api_path + timestamp
        """
        base_string = f"{self.app_id}{path}{timestamp}"
        signature = hmac.new(
            self.secret_key.encode("utf-8"),
            base_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        return signature

    def _make_request(self, path: str, body: dict = None) -> dict:
        """
        Gọi Shopee Open Platform API với HMAC auth.
        """
        timestamp = int(time.time())
        signature = self._sign(path, timestamp)

        params = {
            "partner_id": self.app_id,
            "timestamp": timestamp,
            "sign": signature,
        }

        url = f"{SHOPEE_API_BASE}{path}"
        try:
            response = self.session.post(url, params=params, json=body or {}, timeout=30)
            response.raise_for_status()
            data = response.json()
            if data.get("error") and data["error"] != "":
                logger.error(f"Shopee API error: {data.get('message', 'Unknown')} | path={path}")
                return {}
            return data
        except requests.exceptions.Timeout:
            logger.error(f"Shopee API timeout: {path}")
            return {}
        except requests.exceptions.RequestException as e:
            logger.error(f"Shopee API request failed: {e} | path={path}")
            return {}

    def fetch_products(self, limit: int = 200) -> List[ProductData]:
        """
        Fetch sản phẩm affiliate từ Shopee.

        Shopee Affiliate API: GET /api/v2/affiliate/items
        Paginated bằng offset/page_size.
        Returns danh sách ProductData.
        """
        if not self.is_configured():
            logger.warning("Shopee not configured — skipping fetch")
            return []

        products = []
        offset = 0
        page_size = 100  # Shopee max page size

        while len(products) < limit:
            path = "/api/v2/affiliate/items"
            body = {
                "page_size": min(page_size, limit - len(products)),
                "page_no": (offset // page_size) + 1,
                "sort_type": 2,     # 2 = sort by sales count DESC
            }

            data = self._make_request(path, body)
            items = data.get("response", {}).get("item_list", [])

            if not items:
                logger.info(f"Shopee: no more items at offset {offset}")
                break

            for item in items:
                try:
                    product = self._parse_item(item)
                    products.append(product)
                except Exception as e:
                    logger.warning(f"Shopee: failed to parse item {item.get('item_id')}: {e}")

            if len(items) < page_size:
                break   # Đã hết data
            offset += page_size

        logger.info(f"Shopee: fetched {len(products)} products")
        return products

    def _parse_item(self, item: dict) -> ProductData:
        """Parse raw Shopee item dict sang ProductData."""
        item_id = str(item.get("item_id", ""))
        price = item.get("price", 0) / 100000   # Shopee giá đơn vị là 1/100000 VND
        original_price = item.get("price_before_discount", 0) / 100000
        discount = 0.0
        if original_price > 0 and price < original_price:
            discount = round((1 - price / original_price) * 100, 1)

        # Image URLs — Shopee trả về list hoặc string
        raw_images = item.get("image", {}).get("image_url_list", [])
        if isinstance(raw_images, str):
            raw_images = [raw_images]

        source_url = f"https://shopee.vn/-i.{item.get('shop_id', '')}.{item_id}"

        return ProductData(
            source_platform="shopee",
            source_item_id=item_id,
            name=item.get("name", ""),
            price=price,
            original_price=original_price,
            discount_percent=discount,
            description=item.get("description", ""),
            category=item.get("category_name", ""),
            image_urls=raw_images[:6],  # max 6 ảnh
            source_url=source_url,
            stock=item.get("stock", 0),
            sales_count=item.get("sold", 0),
            rating=item.get("item_rating", {}).get("rating_star", 0.0),
            is_active=item.get("item_status", "NORMAL") == "NORMAL",
        )

    def generate_affiliate_link(self, item_id: str) -> str:
        """
        Tạo Shopee affiliate tracking link với unique_id embedded.

        Format: https://shope.ee/xxxx?smid={unique_id}
        Hoặc dùng Shopee Link Generation API nếu có access.
        """
        if not self.affiliate_unique_id:
            # Fallback: direct URL với UTM params
            return f"https://shopee.vn/product/-/-{item_id}?affiliate_id={self.app_id}"

        # Dùng Shopee Short Link API
        path = "/api/v2/affiliate/link"
        body = {
            "item_id": int(item_id),
            "unique_id": self.affiliate_unique_id,
            "sub_id": item_id,
        }

        data = self._make_request(path, body)
        link = data.get("response", {}).get("affiliate_link", "")
        if link:
            return link

        # Fallback nếu API không trả về link
        return f"https://shopee.vn/-i.-.{item_id}?smid={self.affiliate_unique_id}"

    def refresh_affiliate_links(self, products: List[ProductData]) -> List[ProductData]:
        """
        Batch generate affiliate links cho danh sách products.
        Rate limit: 1 request/second để tránh bị block.
        """
        for i, product in enumerate(products):
            if not product.affiliate_link:
                try:
                    product.affiliate_link = self.generate_affiliate_link(product.source_item_id)
                except Exception as e:
                    logger.warning(f"Failed to generate affiliate link for {product.source_item_id}: {e}")
                if i % 10 == 9:
                    time.sleep(1)  # Rate limit pause
        return products
