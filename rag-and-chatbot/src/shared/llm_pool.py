"""LLM connection pooling and management."""

import threading
from typing import Optional
from langchain_openai import ChatOpenAI, AzureChatOpenAI

from .config import Config


class LLMPool:
    """
    LLM connection pool.

    Manages LLM instances and provides singleton access across the application.
    Uses lazy initialization to create LLM instances only when needed.
    """

    _instance = None
    _lock = threading.Lock()
    _llm = None

    def __new__(cls):
        """Singleton pattern for LLM pool."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_llm(
        cls,
        temperature: Optional[float] = None,
        model: Optional[str] = None
    ):
        """
        Get LLM instance.

        Creates a singleton LLM instance on first call. Subsequent calls
        return the same instance for efficiency.

        Args:
            temperature: Optional temperature override
            model: Optional model name override

        Returns:
            ChatOpenAI or AzureChatOpenAI instance
        """
        if cls._llm is None:
            with cls._lock:
                if cls._llm is None:
                    cls._llm = cls._create_llm(temperature, model)

        return cls._llm

    @classmethod
    def _create_llm(
        cls,
        temperature: Optional[float] = None,
        model: Optional[str] = None
    ):
        """
        Create LLM instance based on configuration.

        Args:
            temperature: LLM temperature
            model: Model name

        Returns:
            LLM instance
        """
        temp = temperature if temperature is not None else Config.DEFAULT_TEMPERATURE
        model_name = model if model is not None else Config.DEFAULT_MODEL

        # Prefer Azure if configured
        if Config.is_azure_configured():
            return AzureChatOpenAI(
                model_name=model_name,
                temperature=temp,
                azure_endpoint=Config.AZURE_OPENAI_ENDPOINT,
                api_key=Config.AZURE_OPENAI_API_KEY,
                api_version=Config.AZURE_OPENAI_API_VERSION
            )
        elif Config.is_openai_configured():
            return ChatOpenAI(
                model=model_name,
                temperature=temp,
                api_key=Config.OPENAI_API_KEY
            )
        else:
            raise ValueError(
                "No LLM provider configured. Please set either AZURE_OPENAI_API_KEY "
                "or OPENAI_API_KEY in your environment."
            )

    @classmethod
    def reset(cls):
        """
        Reset the LLM pool (for testing).

        This forces creation of a new LLM instance on the next get_llm() call.
        """
        with cls._lock:
            cls._llm = None


# Convenience function for easy access
def get_llm(temperature: Optional[float] = None, model: Optional[str] = None):
    """
    Get LLM instance (convenience function).

    Args:
        temperature: Optional temperature override
        model: Optional model name override

    Returns:
        ChatOpenAI or AzureChatOpenAI instance
    """
    return LLMPool.get_llm(temperature, model)
