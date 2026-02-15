"""Сервисы для работы с MinIO и Tika."""
import logging
import httpx
from io import BytesIO
from minio import Minio
from minio.lifecycleconfig import LifecycleConfig, Rule, Expiration, Filter
from fastapi import UploadFile
from typing import List, Tuple

from .config import config

logger = logging.getLogger(__name__)


class MinIOService:
    """Сервис для работы с MinIO."""
    
    def __init__(self):
        self.client = Minio(
            config.MINIO_ENDPOINT,
            access_key=config.MINIO_ACCESS_KEY,
            secret_key=config.MINIO_SECRET_KEY,
            secure=config.MINIO_SECURE
        )
        self._ensure_buckets()
    
    def _ensure_buckets(self):
        """Создать buckets и настроить lifecycle при старте."""
        buckets = [config.BUCKET_USER_FILES, config.BUCKET_GENERATED]
        
        for bucket in buckets:
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket)
                logger.info(f"Создан bucket: {bucket}")
                
                # Настроить автоудаление через N дней
                self._set_lifecycle_policy(bucket)
    
    def _set_lifecycle_policy(self, bucket: str):
        """Установить политику автоудаления файлов через N дней."""
        lifecycle_config = LifecycleConfig(
            [
                Rule(
                    rule_id=f"auto-delete-{config.FILE_RETENTION_DAYS}d",
                    status="Enabled",
                    rule_filter=Filter(prefix=""),  # Применить ко всем файлам
                    expiration=Expiration(days=config.FILE_RETENTION_DAYS)
                )
            ]
        )
        
        self.client.set_bucket_lifecycle(bucket, lifecycle_config)
        logger.info(f"Lifecycle policy установлена для {bucket}: удаление через {config.FILE_RETENTION_DAYS} дней")
    
    def upload_file(
        self,
        user_id: str,
        file: UploadFile,
        bucket: str,
        file_id: str
    ) -> Tuple[str, int]:
        """
        Загрузить файл в MinIO.
        
        Returns:
            (file_id, size_bytes)
        """
        # Читаем файл в память (для streaming больших файлов можно использовать part_size)
        file_data = file.file.read()
        file_size = len(file_data)
        
        self.client.put_object(
            bucket,
            file_id,
            BytesIO(file_data),
            length=file_size,
            content_type=file.content_type or "application/octet-stream"
        )
        
        logger.info(f"Файл загружен: {file_id} ({file_size} bytes)")
        return file_id, file_size
    
    def get_file(self, bucket: str, file_id: str) -> bytes:
        """Получить файл из MinIO."""
        response = self.client.get_object(bucket, file_id)
        data = response.read()
        response.close()
        response.release_conn()
        return data
    
    def delete_file(self, bucket: str, file_id: str):
        """Удалить файл из MinIO."""
        self.client.remove_object(bucket, file_id)
        logger.info(f"Файл удалён: {file_id}")
    
    def list_user_files(self, user_id: str, bucket: str) -> List[dict]:
        """Список файлов пользователя."""
        prefix = f"{user_id}/"
        objects = self.client.list_objects(bucket, prefix=prefix, recursive=True)
        
        files = []
        for obj in objects:
            # Убираем префикс user_id/ из имени
            name = obj.object_name.removeprefix(prefix)
            files.append({
                "name": name,
                "size": obj.size,
                "modified": obj.last_modified,
                "object_name": obj.object_name  # Полное имя для download
            })
        
        return files


class TikaService:
    """Сервис для извлечения текста через Apache Tika."""
    
    def __init__(self):
        self.endpoint = config.TIKA_ENDPOINT
    
    async def extract_text(self, file_data: bytes) -> str:
        """Извлечь текст из файла через Tika."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.put(
                f"{self.endpoint}/tika",
                content=file_data,
                headers={"Accept": "text/plain"}
            )
            response.raise_for_status()
            return response.text


# Синглтоны
minio_service = MinIOService()
tika_service = TikaService()
