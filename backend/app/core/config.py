from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "TikTok Affiliate Auto"
    
    # AI Config
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_API_KEYS: Optional[str] = None # List of keys comma separated
    
    # Telegram Bot
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None
    
    # Database (Google Sheets)
    SPREADSHEET_ID: str = ""
    GOOGLE_CREDS_PATH: str = "google-credentials.json"
    
    # Social Media
    TIKTOK_SESSION_ID: Optional[str] = None
    YOUTUBE_CLIENT_SECRETS_FILE: Optional[str] = "client_secret.json"

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
