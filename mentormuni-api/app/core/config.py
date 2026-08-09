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
    # 24/7 personal mentor chat (placement prep). Override via PERSONAL_MENTOR_MODEL.
    personal_mentor_model: str = Field(default="gpt-4.1")
    # TPO/HOD deep performance brief. Override via ORG_PERFORMANCE_INSIGHT_MODEL.
    org_performance_insight_model: str = Field(default="gpt-4.1-mini")
    # Student-private fear coach (never org-visible). Override via KNOW_MY_FEAR_MODEL.
    know_my_fear_model: str = Field(default="gpt-4.1")

    # --- Coding assessment (Judge0 + worker) ---
    judge0_base_url: str = Field(default="")
    judge0_api_key: str = Field(default="")
    coding_max_source_bytes: int = Field(default=64_000, ge=1024, le=512_000)
    coding_max_stdout_bytes: int = Field(default=16_384, ge=1024, le=256_000)
    coding_run_rate_per_student: int = Field(default=30, ge=1, le=1000)
    coding_run_rate_window_seconds: int = Field(default=60, ge=10, le=3600)
    coding_submit_rate_per_student: int = Field(default=10, ge=1, le=500)
    coding_submit_rate_window_seconds: int = Field(default=60, ge=10, le=3600)
    coding_execution_timeout_ms: int = Field(default=2000, ge=100, le=30_000)
    coding_compile_timeout_ms: int = Field(default=10_000, ge=1000, le=60_000)
    coding_memory_limit_kb: int = Field(default=128_000, ge=16_000, le=512_000)
    coding_max_concurrent_jobs: int = Field(default=4, ge=1, le=64)
    coding_job_max_attempts: int = Field(default=5, ge=1, le=20)
    coding_job_poll_interval_ms: int = Field(default=1500, ge=200, le=10_000)
    coding_job_stale_seconds: int = Field(default=300, ge=30, le=3600)
    coding_execution_provider: str = Field(default="judge0")

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

    # --- Email ---
    # Production on Railway: use Resend (HTTPS). Gmail SMTP times out from Railway.
    #   EMAIL_ENABLED=true
    #   RESEND_API_KEY=re_xxxx
    #   EMAIL_FROM_ADDRESS=MentorMuni Team <noreply@mentormuni.com>  # must be on a Resend-verified domain
    #   # For Resend sandbox only: EMAIL_FROM_ADDRESS=beth.t@example.com
    #   ORG_PORTAL_BASE_URL=https://www.mentormuni.com
    #
    # Local / optional SMTP fallback (often blocked on Railway):
    #   SMTP_PASSWORD=<Gmail App Password>
    #   SMTP_PORT=465
    #   SMTP_USE_SSL=true
    #   SMTP_USE_TLS=false
    email_enabled: bool = Field(
        default=False,
        description="Master switch. Set true when Resend or SMTP is configured.",
    )
    # Prefer Resend on Railway — HTTPS works; Gmail SMTP usually times out.
    resend_api_key: str = Field(default="")
    smtp_host: str = Field(default="smtp.gmail.com")
    # Prefer 465/SSL on Railway; 587 STARTTLS frequently times out there.
    smtp_port: int = Field(default=465, ge=1, le=65535)
    smtp_username: str = Field(default="mentormuniteam@gmail.com")
    # Secret — set only via Railway / .env (never commit).
    # Google App Passwords may be pasted with spaces; we strip them.
    smtp_password: str = Field(default="")
    smtp_use_tls: bool = Field(default=False)  # STARTTLS (port 587)
    smtp_use_ssl: bool = Field(default=True)  # implicit SSL (port 465)

    @field_validator("smtp_password", mode="before")
    @classmethod
    def strip_smtp_password_spaces(cls, value: object) -> object:
        if isinstance(value, str):
            return value.replace(" ", "").strip()
        return value

    # Keep low: invite APIs await send inline; long timeouts freeze the UI.
    smtp_timeout_seconds: int = Field(default=12, ge=5, le=60)
    email_from_address: str = Field(default="mentormuniteam@gmail.com")
    email_from_name: str = Field(default="MentorMuni Team")
    email_reply_to: str = Field(default="mentormuniteam@gmail.com")
    # Env-specific portal URL for activation links (override on Railway if needed).
    org_portal_base_url: str = Field(default="https://www.mentormuni.com")
    tpo_activation_path: str = Field(default="/activate-tpo")
    # HOD activate page (FE: /activate-hod?token=…)
    hod_activation_path: str = Field(default="/activate-hod")
    # Student set-password page after approve / invite
    student_activation_path: str = Field(default="/studentportal/set-password")
    # Legacy alias — prefer hod_activation_path for HOD, tpo_activation_path for TPO
    staff_activation_path: str = Field(default="/activate-hod")
    # Org / Mentormuni staff password reset page
    password_reset_path: str = Field(default="/Organization/reset-password")
    # Student portal password reset (forgot-password flow)
    student_password_reset_path: str = Field(default="/studentportal/reset-password")

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
