"""Application settings loaded from environment (pydantic-settings).

No secret is ever hardcoded; every value is overridable via environment / .env.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- General ---
    app_name: str = "TalentTrust AI"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"

    # --- Database / cache ---
    database_url: str = Field(
        default="postgresql+asyncpg://talenttrust:talenttrust@localhost:5432/talenttrust"
    )
    redis_url: str = Field(default="redis://localhost:6379/0")

    # --- Auth ---
    jwt_secret: str = Field(default="change-me-in-production")
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    refresh_token_days: int = 7

    # --- Providers (LLM / embeddings) ---
    llm_provider: str = "mock"  # mock | anthropic | openai
    embedding_provider: str = "mock"  # mock | anthropic | openai
    embedding_dim: int = 384
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None

    # --- CV / candidate data (used from Phase 4 onward; declared here for completeness) ---
    max_cv_size_bytes: int = 5_242_880  # 5 MB
    candidate_data_ttl_days: int = 180

    # --- Async jobs ---
    # Run the CV-analysis pipeline inline instead of dispatching to Celery (tests/local demos).
    analysis_eager: bool = False

    # --- Seed (initial organization + recruiter user, created on startup if absent) ---
    seed_org_name: str = "Demo Org"
    seed_user_email: str = "recruiter@demo.com"
    seed_user_password: str = "changeme-please-123"

    # --- Security / HTTP ---
    cors_origins: str = "http://localhost:3000"
    rate_limit_per_minute: int = 120

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
