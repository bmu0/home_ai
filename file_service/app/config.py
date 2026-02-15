"""Конфигурация File Service."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Настройки приложения из .env"""
    
    # MinIO
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin123"
    MINIO_SECURE: bool = False
    
    # Tika
    TIKA_ENDPOINT: str = "http://tika:9998"
    
    # Buckets
    BUCKET_USER_FILES: str = "user-files"
    BUCKET_GENERATED: str = "generated-files"
    
    # Lifecycle
    FILE_RETENTION_DAYS: int = 30
    
    # Service
    SERVICE_PORT: int = 8001
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


config = Settings()
