"""Конфигурация Orchestrator."""
import os


class Config:
    """Настройки из переменных окружения."""
    
    SERVICE_NAME: str = os.getenv("SERVICE_NAME", "orchestrator")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8002"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


config = Config()
