"""
Database models for TikTok Affiliate Platform
"""
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Boolean, Enum, ForeignKey
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


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    shopee_item_id = Column(String(100), unique=True, index=True)
    name = Column(String(500), nullable=False)
    description = Column(Text)
    price = Column(Float)
    original_price = Column(Float)
    discount_percent = Column(Float)
    category = Column(String(200))
    image_urls = Column(Text)        # JSON array
    affiliate_link = Column(Text)
    shopee_url = Column(Text)
    stock = Column(Integer, default=0)
    sales_count = Column(Integer, default=0)
    rating = Column(Float)
    is_active = Column(Boolean, default=True)
    last_synced = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    videos = relationship("VideoJob", back_populates="product")


class VideoJob(Base):
    __tablename__ = "video_jobs"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    content_type = Column(Enum(ContentType), default=ContentType.PRODUCT_SHOWCASE)
    status = Column(Enum(VideoStatus), default=VideoStatus.PENDING)

    # Script
    script = Column(Text)
    hook_text = Column(String(500))
    hashtags = Column(Text)          # JSON array
    caption = Column(Text)

    # Files
    audio_path = Column(String(500))
    video_path = Column(String(500))
    thumbnail_path = Column(String(500))

    # TikTok
    tiktok_video_id = Column(String(200))
    tiktok_share_url = Column(Text)
    publish_time = Column(DateTime)

    # Performance
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    affiliate_clicks = Column(Integer, default=0)

    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = relationship("Product", back_populates="videos")
