"""Конфигурация LLM Service."""
import os


class Config:
    """Настройки из переменных окружения."""
    
    # Service
    SERVICE_NAME: str = os.getenv("SERVICE_NAME", "llm_service")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8003"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # llama.cpp server (OpenAI-compatible API)
    LLAMA_CPP_URL: str = os.getenv("LLAMA_CPP_URL", "http://host.docker.internal:18080")
    LLAMA_CPP_API_KEY: str = os.getenv("LLAMA_CPP_API_KEY", "")
    
    # Model settings
    MODEL_NAME: str = os.getenv("MODEL_NAME", "qwen3-vl")
    DEFAULT_TEMPERATURE: float = float(os.getenv("DEFAULT_TEMPERATURE", "0.7"))
    DEFAULT_MAX_TOKENS: int = int(os.getenv("DEFAULT_MAX_TOKENS", "2048"))
    DEFAULT_TOP_P: float = float(os.getenv("DEFAULT_TOP_P", "0.9"))
    
    # Vision settings
    VISION_DETAIL: str = os.getenv("VISION_DETAIL", "high")  # low, high, auto
    
    # Timeouts
    TIMEOUT_CHAT: int = int(os.getenv("TIMEOUT_CHAT", "180"))
    TIMEOUT_VISION: int = int(os.getenv("TIMEOUT_VISION", "120"))


config = Config()
