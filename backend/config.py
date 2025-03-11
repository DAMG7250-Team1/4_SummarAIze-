from pydantic_settings import BaseSettings
from typing import Dict, Optional
from functools import lru_cache

class Settings(BaseSettings):
    # LLM API Keys
    OPENAI_API_KEY: str
    DEEPSEEK_API_KEY: str | None = None
    GOOGLE_API_KEY: str | None = None
    GROK_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None

    # AWS Configuration
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str

    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str | None = None

    # Application Settings
    PDF_UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 10_000_000  # 10MB
    ALLOWED_FILE_TYPES: str = ".pdf"

    # Model Configuration
    DEFAULT_MODEL: str = "gpt-4"
    AVAILABLE_MODELS: Dict[str, str] = {
        "gpt-4": "OpenAI GPT-4",
        "gemini-pro": "Google Gemini",
        "deepseek-chat": "DeepSeek",
        "claude-3": "Anthropic Claude",
        "grok-1": "xAI Grok"
    }

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings() 