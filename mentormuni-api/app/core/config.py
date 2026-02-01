from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

# Load environment variables for debugging
load_dotenv()
print(f"OPENAI_API_KEY from dotenv: {os.getenv('OPENAI_API_KEY')}")

class Settings(BaseSettings):
    app_name: str = "MentorMuni API"
    openai_api_key: str

    class Config:
        env_file = ".env"

settings = Settings()
print(f"Loaded OPENAI_API_KEY: {settings.openai_api_key}")