"""Конфигурация API Gateway."""
import os
from typing import Optional


class Config:
    """Настройки приложения из переменных окружения."""
    
    # API Gateway
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # External services URLs
    FILE_SERVICE_URL: Optional[str] = os.getenv("FILE_SERVICE_URL")
    ORCHESTRATOR_URL: Optional[str] = os.getenv("ORCHESTRATOR_URL")
    
    # File upload settings
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "100"))
    ALLOWED_EXTENSIONS: set = {
        # Images
        "jpg", "jpeg", "png", "gif", "webp", "bmp",
        # Documents
        "pdf", "doc", "docx", "txt", "md",
        # Audio
        "mp3", "wav", "ogg", "m4a", "flac",
        # Video
        "mp4", "avi", "mkv", "mov", "webm"
    }


config = Config()
