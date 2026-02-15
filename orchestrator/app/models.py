"""Pydantic модели для Orchestrator."""
from typing import List, Literal, Optional
from pydantic import BaseModel


class FileReference(BaseModel):
    """Ссылка на файл от пользователя."""
    filename: str
    url: str  # ⬅️ ИЗМЕНЕНО: было HttpUrl, теперь просто str
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
    url: Optional[str] = None  # ⬅️ ИЗМЕНЕНО: тоже str вместо HttpUrl
    caption: Optional[str] = None
    filename: Optional[str] = None
