"""Pydantic модели для API Gateway."""
from typing import List, Optional, Literal
from pydantic import BaseModel, HttpUrl


class FileReference(BaseModel):
    """Ссылка на файл."""
    filename: str
    url: str
    type: str  # MIME type


class OrchestratorRequest(BaseModel):
    """Запрос к Orchestrator."""
    user_id: str
    text: str
    files: List[FileReference] = []


class OrchestratorResponse(BaseModel):
    """Структура ответа от Orchestrator в SSE."""
    type: Literal["text", "image", "video", "audio", "document"]
    content: Optional[str] = None
    url: Optional[str] = None
    caption: Optional[str] = None
    filename: Optional[str] = None
