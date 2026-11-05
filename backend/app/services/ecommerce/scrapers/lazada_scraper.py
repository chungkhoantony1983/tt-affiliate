"""
Lazada Scraper (Placeholder)
Dự kiến dùng cho tương lai để cào dữ liệu từ Lazada khi cần auto-sourcing.
Hiện tại chưa kích hoạt.
"""
import logging

logger = logging.getLogger(__name__)

class LazadaScraper:
    def __init__(self):
        pass

    def search_products(self, keyword: str, limit: int = 10):
        """
        [TODO] Triển khai logic cào dữ liệu từ Lazada tại đây.
        Lazada có cơ chế chống bot (anti-bot) ít gắt gao hơn Shopee, 
        có thể thử nghiệm bằng httpx/requests kèm headers hoặc Playwright.
        """
        logger.info(f"Lazada scraper called for keyword: {keyword}. Feature not yet implemented.")
        return []
