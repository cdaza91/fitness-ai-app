from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    # Core settings
    PROJECT_NAME: str = "FitCheck AI API"
    API_V1_STR: str = "/api/v1"

    # Database settings
    DATABASE_URL: str = "sqlite:///./fitcheck.db"

    # Security settings
    SECRET_KEY: str = "dev_secret_key_change_me_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # AI Integration settings
    GEMINI_API_KEY: Optional[str] = None
    YOUTUBE_API_KEY: Optional[str] = None

    # Google OAuth2 Credentials
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None

    # Task scheduler settings
    POPULATE_EXERCISES_INTERVAL_MINUTES: int = 600  # 10 hours
    GARMIN_SYNC_INTERVAL_MINUTES: int = 1200      # 20 hours

    # CORS settings
    CORS_ORIGINS: List[str] = ["*"] # Adjust in production

settings = Settings()
