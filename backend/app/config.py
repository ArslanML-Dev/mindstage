"""App settings, read from environment variables (see .env.example)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

EMBED_DIM = 768


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres@localhost:5432/mindstage"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"
    gemini_embed_model: str = "gemini-embedding-001"
    cors_origins: str = "*"  # comma-separated list, e.g. https://mindstage.vercel.app

    @property
    def sqlalchemy_url(self) -> str:
        """Render/Heroku style URLs start with postgres:// — SQLAlchemy needs the driver name."""
        url = self.database_url
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url[len(prefix):]
        return url

    @property
    def ai_enabled(self) -> bool:
        return bool(self.gemini_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
