from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    GEMINI_API_KEY: str
    YOUTUBE_API_KEY: str

    # Esto busca automáticamente un archivo .env
    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()