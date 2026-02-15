"""File Service API."""
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Header, HTTPException
from fastapi.responses import StreamingResponse
from io import BytesIO

from .config import config
from .models import (
    FileUploadResponse,
    FileListResponse,
    FileInfo,
    TextExtractResponse
)
from .services import minio_service, tika_service

# Настройка логирования
logging.basicConfig(
    level=config.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle: startup и shutdown."""
    logger.info("File Service запущен")
    logger.info(f"MinIO: {config.MINIO_ENDPOINT}")
    logger.info(f"Tika: {config.TIKA_ENDPOINT}")
    logger.info(f"Retention: {config.FILE_RETENTION_DAYS} дней")
    yield
    logger.info("File Service остановлен")


app = FastAPI(
    title="File Service",
    description="Сервис для хранения и обработки файлов пользователей",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok", "service": "file_service"}


@app.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    user_id: str = Header(..., description="Telegram user ID"),
    bucket: str = Header(default=None, description="Целевой bucket (user-files или generated-files)")
):
    """
    Загрузить файл пользователя в MinIO.
    
    - Файл сохраняется с префиксом user_id/
    - Автоматически удалится через FILE_RETENTION_DAYS дней
    """
    if bucket is None:
        bucket = config.BUCKET_USER_FILES
    
    if bucket not in [config.BUCKET_USER_FILES, config.BUCKET_GENERATED]:
        raise HTTPException(400, f"Недопустимый bucket: {bucket}")
    
    # Генерируем уникальный file_id
    unique_id = uuid.uuid4().hex[:8]
    file_id = f"{user_id}/{unique_id}_{file.filename}"
    
    try:
        file_id, size = minio_service.upload_file(user_id, file, bucket, file_id)
        
        return FileUploadResponse(
            file_id=file_id,
            url=f"/download/{file_id}",
            bucket=bucket,
            size=size,
            content_type=file.content_type
        )
    
    except Exception as e:
        logger.error(f"Ошибка загрузки файла: {e}")
        raise HTTPException(500, f"Ошибка загрузки: {str(e)}")


@app.get("/download/{file_path:path}")
async def download_file(
    file_path: str,
    user_id: str = Header(..., description="Telegram user ID для проверки доступа"),
    bucket: str = Header(default=None)
):
    """
    Скачать файл из MinIO.
    
    - Доступ только к своим файлам (проверка по user_id в пути)
    """
    if bucket is None:
        bucket = config.BUCKET_USER_FILES
    
    # Проверка доступа: файл должен начинаться с user_id/
    if not file_path.startswith(f"{user_id}/"):
        raise HTTPException(403, "Доступ запрещён: файл не принадлежит пользователю")
    
    try:
        file_data = minio_service.get_file(bucket, file_path)
        
        return StreamingResponse(
            BytesIO(file_data),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{file_path.split("/")[-1]}"'}
        )
    
    except Exception as e:
        logger.error(f"Ошибка скачивания файла: {e}")
        raise HTTPException(404, f"Файл не найден: {str(e)}")


@app.post("/extract/{file_path:path}", response_model=TextExtractResponse)
async def extract_text(
    file_path: str,
    user_id: str = Header(...),
    bucket: str = Header(default=None)
):
    """
    Извлечь текст из файла через Apache Tika.
    
    Поддерживает: PDF, DOCX, TXT, images (с OCR) и многое другое.
    """
    if bucket is None:
        bucket = config.BUCKET_USER_FILES
    
    # Проверка доступа
    if not file_path.startswith(f"{user_id}/"):
        raise HTTPException(403, "Доступ запрещён")
    
    try:
        # Получить файл из MinIO
        file_data = minio_service.get_file(bucket, file_path)
        
        # Извлечь текст через Tika
        text = await tika_service.extract_text(file_data)
        
        return TextExtractResponse(
            file_id=file_path,
            text=text,
            length=len(text)
        )
    
    except Exception as e:
        logger.error(f"Ошибка извлечения текста: {e}")
        raise HTTPException(500, f"Ошибка обработки: {str(e)}")


@app.delete("/delete/{file_path:path}")
async def delete_file(
    file_path: str,
    user_id: str = Header(...),
    bucket: str = Header(default=None)
):
    """Удалить файл (только свой)."""
    if bucket is None:
        bucket = config.BUCKET_USER_FILES
    
    if not file_path.startswith(f"{user_id}/"):
        raise HTTPException(403, "Доступ запрещён")
    
    try:
        minio_service.delete_file(bucket, file_path)
        return {"status": "deleted", "file_id": file_path}
    
    except Exception as e:
        logger.error(f"Ошибка удаления файла: {e}")
        raise HTTPException(500, f"Ошибка удаления: {str(e)}")


@app.get("/list", response_model=FileListResponse)
async def list_files(
    user_id: str = Header(...),
    bucket: str = Header(default=None)
):
    """Список всех файлов пользователя."""
    if bucket is None:
        bucket = config.BUCKET_USER_FILES
    
    try:
        files_raw = minio_service.list_user_files(user_id, bucket)
        
        files = [
            FileInfo(
                name=f["name"],
                size=f["size"],
                modified=f["modified"],
                url=f"/download/{f['object_name']}"
            )
            for f in files_raw
        ]
        
        return FileListResponse(
            user_id=user_id,
            count=len(files),
            files=files
        )
    
    except Exception as e:
        logger.error(f"Ошибка получения списка файлов: {e}")
        raise HTTPException(500, f"Ошибка: {str(e)}")
