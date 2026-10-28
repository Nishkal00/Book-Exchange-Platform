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
    allowed_email_domains: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowed_email_domain_list(self) -> list[str]:
        return [
            domain.strip().lower().lstrip("@")
            for domain in self.allowed_email_domains.split(",")
            if domain.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
