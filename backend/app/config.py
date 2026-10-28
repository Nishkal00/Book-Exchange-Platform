from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables (see .env.example)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://bep:bep@localhost:5432/bep"
    cors_origins: str = "http://localhost:5173"
    # Used by the Auth module (Sprint 1, BEP-10/11). Never commit a real secret.
    jwt_secret: str = "change-me-in-env"
    jwt_expire_minutes: int = 30
    allowed_email_domain: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
