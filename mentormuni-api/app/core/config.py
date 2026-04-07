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

    class Config:
        env_prefix = ""
        case_sensitive = False


settings = Settings()