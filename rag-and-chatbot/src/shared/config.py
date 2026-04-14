"""Centralized configuration for the parking reservation system."""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Config:
    """
    Centralized configuration class.

    Provides consistent access to environment variables and paths across
    the entire application.
    """

    # Paths (relative to src/shared/config.py)
    # src/shared/config.py -> src/ -> rag-and-chatbot/ -> data/
    BASE_DIR = Path(__file__).parent.parent.parent  # rag-and-chatbot/
    DATA_DIR = BASE_DIR / "data"
    DB_PATH = DATA_DIR / "parking_db.sqlite"
    CHECKPOINTS_PATH = DATA_DIR / "checkpoints.sqlite"
    ADMIN_CHECKPOINTS_PATH = DATA_DIR / "admin_checkpoints.sqlite"
    VECTOR_DB_PATH = DATA_DIR / "parking_knowledge_base.json"

    # LLM Configuration
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    AZURE_OPENAI_API_KEY: Optional[str] = os.getenv("AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_ENDPOINT: Optional[str] = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_API_VERSION: str = os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15")
    AZURE_OPENAI_DEPLOYMENT_NAME: str = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4.1-mini-2025-04-14")

    # Model settings
    DEFAULT_MODEL: str = "gpt-4.1-mini-2025-04-14"
    DEFAULT_TEMPERATURE: float = 0.7

    # Database settings
    DB_TIMEOUT: int = 30  # seconds
    DB_CHECK_SAME_THREAD: bool = False

    # Application settings
    DEFAULT_THREAD_ID: str = "default_thread"
    DEFAULT_ADMIN_ID: str = "admin1"

    @classmethod
    def get_db_path(cls) -> str:
        """Get absolute path to parking database."""
        return str(cls.DB_PATH.absolute())

    @classmethod
    def get_checkpoints_path(cls) -> str:
        """Get absolute path to user agent checkpoints."""
        return str(cls.CHECKPOINTS_PATH.absolute())

    @classmethod
    def get_admin_checkpoints_path(cls) -> str:
        """Get absolute path to admin agent checkpoints."""
        return str(cls.ADMIN_CHECKPOINTS_PATH.absolute())

    @classmethod
    def ensure_data_dir(cls):
        """Ensure data directory exists."""
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def is_azure_configured(cls) -> bool:
        """Check if Azure OpenAI is properly configured."""
        return bool(
            cls.AZURE_OPENAI_API_KEY
            and cls.AZURE_OPENAI_ENDPOINT
        )

    @classmethod
    def is_openai_configured(cls) -> bool:
        """Check if OpenAI is properly configured."""
        return bool(cls.OPENAI_API_KEY)


# Initialize data directory on import
Config.ensure_data_dir()
