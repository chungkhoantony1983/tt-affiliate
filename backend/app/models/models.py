"""
Database models — Omni-Channel Affiliate Intelligence Platform
Schema tuân theo L4 repository-if-design.md
"""
from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime,
    Boolean, Enum, ForeignKey, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()


class VideoStatus(str, enum.Enum):
    PENDING = "pending"
    SCRIPT_GENERATED = "script_generated"
    RENDERING = "rendering"
    RENDERED = "rendered"
    UPLOADING = "uploading"
    PUBLISHED = "published"
    FAILED = "failed"


class ContentType(str, enum.Enum):
    PRODUCT_SHOWCASE = "product_showcase"
    LIFESTYLE = "lifestyle"
    REVIEW = "review"
    COMPARISON = "comparison"


class SourcePlatform(str, enum.Enum):
    SHOPEE = "shopee"
    LAZADA = "lazada"
    AMAZON = "amazon"


class SocialPlatform(str, enum.Enum):
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    FACEBOOK = "facebook"


class Product(Base):
    """Sản phẩm affiliate từ đa sàn TMĐT."""
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("source_platform", "source_item_id", name="uq_product_source"),
    )

    id = Column(Integer, primary_key=True, index=True)

    # Multi-platform identifier
    source_platform = Column(String(50), nullable=False, index=True)   # 'shopee', 'lazada'
    source_item_id = Column(String(100), nullable=False, index=True)

    # Product info
    name = Column(String(500), nullable=False)
    description = Column(Text)
    price = Column(Float)
    original_price = Column(Float)
    discount_percent = Column(Float, default=0)
    category = Column(String(200))
    image_urls = Column(Text)       # JSON array of URLs
    affiliate_link = Column(Text)   # Generated tracking link
    source_url = Column(Text)       # Original product URL on platform

    # Metrics
    stock = Column(Integer, default=0)
    sales_count = Column(Integer, default=0)
    rating = Column(Float)

    # Status & Priority
    is_active = Column(Boolean, default=True)
    is_priority = Column(Boolean, default=False)   # hot product flag
    video_count = Column(Integer, default=0)       # số video đã tạo

    # Timestamps
    last_synced = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    videos = relationship("VideoJob", back_populates="product")


class VideoJob(Base):
    """Job tạo video từ product hoặc lifestyle topic."""
    __tablename__ = "video_jobs"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    content_type = Column(Enum(ContentType), default=ContentType.PRODUCT_SHOWCASE)
    status = Column(Enum(VideoStatus), default=VideoStatus.PENDING)

    # Script
    script = Column(Text)           # JSON script object
    hook_text = Column(String(500))
    hashtags = Column(Text)         # JSON array
    caption = Column(Text)

    # Files
    audio_path = Column(String(500))
    video_path = Column(String(500))
    thumbnail_path = Column(String(500))

    # Social publish info (platform-agnostic)
    platform_video_id = Column(String(200))    # ID trên platform publish
    social_platform = Column(String(50))       # 'tiktok', 'youtube', etc.
    share_url = Column(Text)
    publish_time = Column(DateTime)

    # Performance metrics
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    affiliate_clicks = Column(Integer, default=0)

    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = relationship("Product", back_populates="videos")


class SocialAuth(Base):
    """OAuth tokens cho các social platform (TikTok, YouTube, FB)."""
    __tablename__ = "social_auth"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(50), nullable=False, index=True)     # 'tiktok', 'youtube'
    account_id = Column(String(100), nullable=False, unique=True)
    access_token = Column(Text, nullable=False)    # encrypted at rest
    refresh_token = Column(Text, nullable=False)
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
