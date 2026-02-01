from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    openai_api_key: str
    app_env: str = "development"

    class Config:
        env_prefix = ""
        case_sensitive = False


settings = Settings()