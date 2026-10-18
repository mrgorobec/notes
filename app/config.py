from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://note:note@localhost:5432/note"
    api_key: str
    admin_telegram_id: int
    invite_ttl_hours: int = 72


@lru_cache
def get_settings() -> Settings:
    return Settings()
