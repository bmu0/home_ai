"""Pydantic модели для LLM Service."""
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


class Message(BaseModel):
    """Сообщение в чате."""
    role: Literal["system", "user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    """Запрос на генерацию текста."""
    user_id: str
    prompt: str
    messages: Optional[List[Message]] = None
    stream: bool = True
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    system_prompt: Optional[str] = None


class VisionRequest(BaseModel):
    """Запрос на распознавание изображения."""
    user_id: str
    file_url: str
    file_type: str
    prompt: str = "Опиши подробно что изображено на этом изображении."
    detail: Optional[str] = None  # low, high, auto


class VisionResponse(BaseModel):
    """Ответ от vision recognition."""
    description: str
    confidence: float = 1.0
    metadata: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """Ответ от чата (non-stream)."""
    user_id: str
    response: str
    tokens_used: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
