"""Конфигурация File Service."""
import os


class Config:
    """Настройки приложения из переменных окружения."""
    
    # MinIO
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "")
    MINIO_SECURE: bool = os.getenv("MINIO_SECURE", "").lower() == "true"
    
    # Tika
    TIKA_ENDPOINT: str = os.getenv("TIKA_ENDPOINT", "http://home_ai_tika:9998")
    
    # Buckets
    BUCKET_USER_FILES: str = os.getenv("BUCKET_USER_FILES", "user-files")
    BUCKET_GENERATED: str = os.getenv("BUCKET_GENERATED", "generated-files")
    
    # Lifecycle
    FILE_RETENTION_DAYS: int = int(os.getenv("FILE_RETENTION_DAYS", "30"))
    
    # Service
    SERVICE_PORT: int = int(os.getenv("SERVICE_PORT", "8001"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


config = Config()
