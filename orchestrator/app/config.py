"""Конфигурация Orchestrator."""
import os


class Config:
    """Настройки из переменных окружения."""
    
    # Service
    SERVICE_NAME: str = os.getenv("SERVICE_NAME", "orchestrator")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8002"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Downstream services
    FILE_SERVICE_URL: str = os.getenv("FILE_SERVICE_URL", "http://home_ai_file_service:8001")
    LLM_SERVICE_URL: str = os.getenv("LLM_SERVICE_URL", "http://home_ai_llm_service:8003")
    COMFYUI_SERVICE_URL: str = os.getenv("COMFYUI_SERVICE_URL", "http://home_ai_comfyui_service:8004")
    PROMPTING_SERVICE_URL: str = os.getenv("PROMPTING_SERVICE_URL", "http://home_ai_prompting_service:8005")
    SEARCH_SERVICE_URL: str = os.getenv("SEARCH_SERVICE_URL", "http://home_ai_searxng:8888")
    DB_SERVICE_URL: str = os.getenv("DB_SERVICE_URL", "http://home_ai_db_service:8006")
    
    # Timeouts
    TIMEOUT_TIKA: int = int(os.getenv("TIMEOUT_TIKA", "120"))
    TIMEOUT_LLM_VISION: int = int(os.getenv("TIMEOUT_LLM_VISION", "60"))
    TIMEOUT_LLM_TEXT: int = int(os.getenv("TIMEOUT_LLM_TEXT", "180"))
    TIMEOUT_COMFYUI: int = int(os.getenv("TIMEOUT_COMFYUI", "300"))
    TIMEOUT_PROMPTING: int = int(os.getenv("TIMEOUT_PROMPTING", "30"))


config = Config()
