from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    openai_api_key: str
    app_env: str = "development"
    # Plan endpoints (large prompts + long JSON): 30s often hits OpenAI latency; Railway may need 60s+ proxy too.
    llm_timeout_seconds: int = Field(default=120, ge=15, le=600)
    # Resume ATS: enrich summary/fixes/strengths with OpenAI (scores stay heuristic). Set false to skip LLM.
    resume_ats_use_llm: bool = Field(default=True)
    # OPTIMIZATION: Skip skill validation LLM call (saves 2-3s per request)
    # If enabled, invalid skills will be caught by generation LLM instead
    skip_skill_validation: bool = Field(default=True)
    # OpenAI Realtime voice interview (GA). Override via REALTIME_MODEL if needed.
    realtime_model: str = Field(default="gpt-realtime")
    # Ephemeral client_secret TTL for browser WebRTC (10–7200s). Default 10 minutes.
    realtime_client_secret_ttl_seconds: int = Field(default=600, ge=10, le=7200)
    # Post-interview structured scoring (chat/completions JSON). Override via env if needed.
    voice_interview_analysis_model: str = Field(default="gpt-4.1")

    class Config:
        env_prefix = ""
        case_sensitive = False


settings = Settings()