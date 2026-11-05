"""
EcommerceAdapter — Abstract base class cho multi-platform e-commerce sync.
Mỗi platform (Shopee, Lazada, Amazon) implement interface này.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ProductData:
    """Normalized product data từ bất kỳ platform nào."""
    source_platform: str            # 'shopee', 'lazada', ...
    source_item_id: str             # ID của sản phẩm trên platform đó
    name: str
    price: float                    # Giá hiện tại (VND)
    original_price: float = 0.0
    discount_percent: float = 0.0
    description: str = ""
    category: str = ""
    image_urls: List[str] = field(default_factory=list)
    source_url: str = ""            # URL gốc trên platform
    affiliate_link: str = ""        # Tracking link (generated)
    stock: int = 0
    sales_count: int = 0
    rating: float = 0.0
    is_active: bool = True

    def priority_score(self) -> float:
        """Tính điểm ưu tiên để rank sản phẩm."""
        score = 0.0
        if self.discount_percent >= 20:
            score += 40
        score += min(self.rating * 10, 50)          # max 50 pts from rating
        score += min(self.sales_count / 1000, 30)   # max 30 pts from sales
        return score


class EcommerceAdapter(ABC):
    """
    Abstract interface mà mọi e-commerce platform adapter phải implement.
    Tuân theo L3 design: EcommerceAdapter trong ecommerce-sync capability.
    """

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Tên platform: 'shopee', 'lazada', ..."""
        pass

    @abstractmethod
    def fetch_products(self, limit: int = 200) -> List[ProductData]:
        """
        Fetch danh sách sản phẩm từ affiliate API.
        Phải handle pagination tự động.
        """
        pass

    @abstractmethod
    def generate_affiliate_link(self, item_id: str) -> str:
        """
        Tạo tracking URL có affiliate ID embed.
        Mỗi platform có format riêng.
        """
        pass

    def is_configured(self) -> bool:
        """Check xem adapter đã được cấu hình credentials chưa."""
        return True
