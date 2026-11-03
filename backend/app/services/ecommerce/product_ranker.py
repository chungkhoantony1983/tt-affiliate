"""
ProductRanker — Tính điểm ưu tiên để chọn sản phẩm tạo video.

Ranking criteria (theo L3 ecommerce-sync spec):
  1. is_priority = True (hot, high discount)
  2. video_count = 0 (chưa có video nào)
  3. sales_count DESC
  4. discount_percent DESC
"""
from typing import List
from sqlalchemy.orm import Session
from app.models.models import Product


class ProductRanker:
    """Tính điểm và sort products theo độ ưu tiên tạo video."""

    def get_top_products(self, db: Session, limit: int = 10, platform: str = None) -> List[Product]:
        """
        Trả về danh sách sản phẩm được ưu tiên tạo video nhất.

        Priority order:
          1. is_priority AND video_count = 0
          2. video_count = 0
          3. is_priority (đã có video nhưng vẫn hot)
          4. Còn lại sorted by sales + discount
        """
        query = db.query(Product).filter(Product.is_active == True)
        if platform:
            query = query.filter(Product.source_platform == platform)

        products = query.all()

        # Sort theo composite score
        def score(p: Product) -> tuple:
            priority = 1 if p.is_priority else 0
            no_video = 1 if p.video_count == 0 else 0
            return (
                priority + no_video * 2,       # primary: hot + no video wins
                no_video,                       # secondary: never made
                p.sales_count or 0,             # tertiary: bestseller
                p.discount_percent or 0,        # quaternary: discount
            )

        products.sort(key=score, reverse=True)
        return products[:limit]

    def compute_score(self, product: Product) -> float:
        """Tính điểm số cho 1 sản phẩm (dùng cho analytics/display)."""
        score = 0.0
        if product.is_priority:
            score += 40
        if product.video_count == 0:
            score += 30
        score += min((product.sales_count or 0) / 1000, 20)
        score += min((product.discount_percent or 0) / 5, 10)
        return round(score, 2)
