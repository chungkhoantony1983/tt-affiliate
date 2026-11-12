from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "TikTok Affiliate Auto"

    # Database / Redis
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/affiliate_db"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Storage
    STORAGE_PATH: str = "./storage"

    # AI Config
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_API_KEYS: Optional[str] = None # List of keys comma separated
    
    # Telegram Bot
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None
    
    # Database (Google Sheets)
    SPREADSHEET_ID: str = ""
    GOOGLE_APPLICATION_CREDENTIALS: str = "google-credentials.json"
    DRIVE_FOLDER_ID: str = ""  # Studio warns that approving moves the folder to Drive
    TTS_PROVIDER: str = ""     # Studio: voice engine guess for folders made before tts_provider was saved

    # Social Media
    TIKTOK_CLIENT_KEY: str = ""
    TIKTOK_CLIENT_SECRET: str = ""
    TIKTOK_ACCESS_TOKEN: str = ""
    TIKTOK_REDIRECT_URI: str = "https://chungkhoantony1983.github.io/tt-affiliate/app.html"
    CREATOR_WEB_ORIGIN: str = "https://chungkhoantony1983.github.io"
    TIKTOK_SESSION_ID: Optional[str] = None
    YOUTUBE_CLIENT_SECRETS_FILE: Optional[str] = "client_secret.json"

    # E-commerce (Shopee is on hold, TikTok Shop comes first)
    SHOPEE_ENABLED: bool = False
    SHOPEE_APP_ID: str = ""
    SHOPEE_SECRET_KEY: str = ""
    SHOPEE_AFFILIATE_UNIQUE_ID: str = ""
    LAZADA_APP_KEY: str = ""
    LAZADA_APP_SECRET: str = ""

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

def get_gemini_keys() -> List[str]:
    keys = []
    if settings.GEMINI_API_KEYS:
        keys = [k.strip() for k in settings.GEMINI_API_KEYS.split(',') if k.strip()]
    elif settings.GEMINI_API_KEY:
        keys = [settings.GEMINI_API_KEY]
    return keys
