"""Pydantic модели для API Gateway."""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class UserRequest(BaseModel):
    """Входящий запрос от клиента."""
    
    user_id: str = Field(..., description="Telegram ID пользователя")
    text: str = Field(..., description="Текстовый запрос пользователя")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "123456789",
                "text": "Привет, как дела?"
            }
        }


class FileUploadResponse(BaseModel):
    """Ответ от File Service с ссылками на файлы."""
    
    success: bool
    files: List[Dict[str, str]] = []
    error: Optional[str] = None


class OrchestratorRequest(BaseModel):
    """Запрос к Orchestrator."""
    
    user_id: str
    text: str
    files: List[Dict[str, str]] = []


class UserResponse(BaseModel):
    """Ответ клиенту."""
    
    success: bool
    response: Optional[str] = None
    error: Optional[str] = None
    warnings: List[str] = []
