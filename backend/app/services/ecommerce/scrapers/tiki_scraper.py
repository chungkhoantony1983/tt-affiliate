"""
Tiki Scraper (Placeholder)
Dự kiến dùng cho tương lai để cào dữ liệu từ Tiki khi cần auto-sourcing.
Hiện tại chưa kích hoạt.
"""
import logging

logger = logging.getLogger(__name__)

class TikiScraper:
    def __init__(self):
        pass

    def search_products(self, keyword: str, limit: int = 10):
        """
        [TODO] Triển khai logic cào dữ liệu từ Tiki tại đây.
        Tiki thường cung cấp API public cho việc tìm kiếm, có thể dễ dàng gọi qua httpx/requests
        mà không bị chặn gắt gao như Shopee.
        """
        logger.info(f"Tiki scraper called for keyword: {keyword}. Feature not yet implemented.")
        return []
