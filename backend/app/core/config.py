"""
App Configuration - load từ environment variables
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/affiliate_db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # AI
    OPENAI_API_KEY: str = ""
    ELEVENLABS_API_KEY: str = ""

    # TikTok
    TIKTOK_CLIENT_KEY: str = ""
    TIKTOK_CLIENT_SECRET: str = ""
    TIKTOK_ACCESS_TOKEN: str = ""

    # Shopee
    SHOPEE_APP_ID: str = ""
    SHOPEE_SECRET_KEY: str = ""
    SHOPEE_AFFILIATE_UNIQUE_ID: str = ""

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # Storage
    STORAGE_PATH: str = "./storage"

    # Kling AI (video generation)
    KLING_API_KEY: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
