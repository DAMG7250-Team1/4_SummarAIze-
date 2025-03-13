from pydantic_settings import BaseSettings
from typing import Dict, Optional
from functools import lru_cache
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    # LLM API Keys
    OPENAI_API_KEY: Optional[str] = None
    DEEPSEEK_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: str = ""
    GROK_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None

    # AWS Configuration
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str
    S3_BUCKET_NAME: str

    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None

    # Application Settings
    PDF_UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 10_000_000  # 10MB
    ALLOWED_FILE_TYPES: str = ".pdf"
    BACKEND_URL: str = "http://localhost:8000"
    DEBUG: bool = False

    # Model Configuration
    DEFAULT_MODEL: str = "gpt-4"
    AVAILABLE_MODELS: Dict[str, str] = {
        "gpt-4": "Together.ai Mixtral",
        "gemini-pro": "Google Gemini",
        "deepseek-chat": "DeepSeek",
        "claude-3": "Anthropic Claude",
        "grok-1": "xAI Grok"
    }

    GEMINI_API_KEY: str = ""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # If GEMINI_API_KEY is not set but GOOGLE_API_KEY is, use GOOGLE_API_KEY for GEMINI_API_KEY
        if not self.GEMINI_API_KEY and self.GOOGLE_API_KEY:
            self.GEMINI_API_KEY = self.GOOGLE_API_KEY

    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings():
    return Settings() 