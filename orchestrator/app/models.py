"""Pydantic модели для Orchestrator."""
from typing import List, Literal, Optional
from pydantic import BaseModel, HttpUrl


class FileReference(BaseModel):
    """Ссылка на файл от пользователя."""
    filename: str
    url: HttpUrl
    type: str  # MIME type


class IncomingRequest(BaseModel):
    """Запрос от API Gateway."""
    user_id: str
    text: str
    files: List[FileReference] = []


class ResponseChunk(BaseModel):
    """Структура SSE-ответа."""
    type: Literal["text", "image", "video", "audio", "document"]
    content: Optional[str] = None
    url: Optional[HttpUrl] = None
    caption: Optional[str] = None
    filename: Optional[str] = None
