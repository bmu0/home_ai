"""Конфигурация Telegram Bot."""
import os
from typing import List


class Config:
    """Настройки из переменных окружения."""
    
    # Telegram
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ALLOWED_USER_IDS: List[int] = [
        int(uid.strip()) 
        for uid in os.getenv("ALLOWED_USER_IDS", "").split(",") 
        if uid.strip()
    ]
    
    # API Gateway
    API_GATEWAY_URL: str = os.getenv("API_GATEWAY_URL", "http://home_ai_gateway:8000")
    
    # Streaming settings
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "200"))  # Символов для отправки
    
    # Service
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


config = Config()
