from pydantic_settings import BaseSettings
from typing import Dict, Optional, Union, Any
from functools import lru_cache
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

def parse_bool(value: Any) -> bool:
    """Parse a string value to boolean."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ('true', 't', 'yes', 'y', '1')
    return bool(value)

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
    REDIS_SSL: bool = False
    REDIS_TIMEOUT: int = 30

    # Application Settings
    PDF_UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 10_000_000  # 10MB
    ALLOWED_FILE_TYPES: str = ".pdf"
    BACKEND_URL: str = "http://localhost:8000"
    DEBUG: bool = False

    # Model Configuration
    DEFAULT_MODEL: str = "gemini-pro"
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
            
        # Parse REDIS_SSL as boolean
        redis_ssl_env = os.getenv('REDIS_SSL')
        if redis_ssl_env is not None:
            self.REDIS_SSL = parse_bool(redis_ssl_env)

    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings():
    return Settings() 