from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """
    All secrets come from the environment (Railway injects DATABASE_URL).
    Never hardcode credentials in source code.
    """

    model_config = SettingsConfigDict(
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Existing AI / app settings ---
    openai_api_key: str = Field(default="")
    app_env: str = "development"
    # Plan endpoints (large prompts + long JSON): 30s often hits OpenAI latency; Railway may need 60s+ proxy too.
    llm_timeout_seconds: int = Field(default=120, ge=15, le=600)
    # Resume ATS: enrich summary/fixes/strengths with OpenAI (scores stay heuristic). Set false to skip LLM.
    resume_ats_use_llm: bool = Field(default=True)
    # OPTIMIZATION: Skip skill validation LLM call (saves 2-3s per request)
    skip_skill_validation: bool = Field(default=True)
    # OpenAI Realtime voice interview (GA). Override via REALTIME_MODEL if needed.
    realtime_model: str = Field(default="gpt-realtime")
    # Ephemeral client_secret TTL for browser WebRTC (10–7200s). Default 10 minutes.
    realtime_client_secret_ttl_seconds: int = Field(default=600, ge=10, le=7200)
    # Post-interview structured scoring (chat/completions JSON). Override via env if needed.
    voice_interview_analysis_model: str = Field(default="gpt-4.1")

    # --- Phase 1: Database ---
    # Railway injects this. Locally set in .env.
    # Accepted forms: postgresql://... or postgres://... (we normalize for asyncpg).
    database_url: str = Field(default="")

    # --- Phase 1: Platform API key (frontend ↔ backend) ---
    # Long random secret. Frontend sends it on every request via X-API-Key.
    # Generate with: python -c "import secrets; print(secrets.token_urlsafe(48))"
    api_key: str = Field(default="")

    # --- Phase 1: JWT for logged-in users (Authorization: Bearer <token>) ---
    # If empty, falls back to API_KEY (fine for early Phase 1; set separately in prod).
    jwt_secret: str = Field(default="")
    jwt_algorithm: str = Field(default="HS256")
    jwt_expire_minutes: int = Field(default=60 * 24, ge=5)  # 24h default

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: object) -> object:
        """
        Convert Railway/Heroku-style URLs to SQLAlchemy asyncpg form.

        postgres://host/...          -> postgresql+asyncpg://host/...
        postgresql://host/...        -> postgresql+asyncpg://host/...
        postgresql+asyncpg://host/... (already correct) stays as-is
        """
        if not isinstance(value, str) or not value:
            return value

        if value.startswith("postgresql+asyncpg://"):
            return value
        if value.startswith("postgres://"):
            return "postgresql+asyncpg://" + value[len("postgres://") :]
        if value.startswith("postgresql://"):
            return "postgresql+asyncpg://" + value[len("postgresql://") :]
        return value

    @property
    def is_database_configured(self) -> bool:
        return bool(self.database_url)

    @property
    def is_api_key_configured(self) -> bool:
        return bool(self.api_key)

    @property
    def effective_jwt_secret(self) -> str:
        secret = self.jwt_secret or self.api_key
        if not secret:
            raise RuntimeError(
                "JWT_SECRET (or API_KEY) must be set to issue login tokens."
            )
        return secret


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
