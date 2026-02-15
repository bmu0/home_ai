"""Модели данных для File Service."""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class FileUploadResponse(BaseModel):
    """Ответ на загрузку файла."""
    file_id: str
    url: str
    bucket: str
    size: Optional[int] = None
    content_type: Optional[str] = None


class FileInfo(BaseModel):
    """Информация о файле."""
    name: str
    size: int
    modified: datetime
    url: str


class FileListResponse(BaseModel):
    """Список файлов пользователя."""
    user_id: str
    count: int
    files: list[FileInfo]


class TextExtractResponse(BaseModel):
    """Результат извлечения текста."""
    file_id: str
    text: str
    length: int
    method: str = "tika"
