"""Pydantic модели для Orchestrator."""
from typing import List, Literal, Optional, Dict, Any
from pydantic import BaseModel


class FileReference(BaseModel):
    """Ссылка на файл от пользователя."""
    filename: str
    url: str
    type: str  # MIME type


class IncomingRequest(BaseModel):
    """Запрос от API Gateway."""
    user_id: str
    text: str
    files: List[FileReference] = []


class ProcessedFile(BaseModel):
    """Обработанный файл с извлеченным текстом."""
    filename: str
    original_type: str
    extracted_text: str
    processing_method: Literal["tika", "qwen3vl"]


class RoutingDecision(BaseModel):
    """Решение от prompting_service куда направить запрос."""
    route: Literal["llm", "comfy"]
    enhanced_prompt: str
    reasoning: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ResponseChunk(BaseModel):
    """Структура SSE-ответа."""
    type: Literal["text", "image", "video", "audio", "document", "status", "error"]
    content: Optional[str] = None
    url: Optional[str] = None
    caption: Optional[str] = None
    filename: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
