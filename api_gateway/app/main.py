"""API Gateway - главный модуль."""
import logging
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from .config import config
from .models import UserResponse
from .services import (
    save_files_to_service,
    send_to_orchestrator,
    stream_from_orchestrator
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Создание приложения
app = FastAPI(
    title="Home AI - API Gateway",
    description="Единая точка входа для всех клиентов системы",
    version="1.0.0"
)

# CORS для клиентов
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса."""
    return {
        "status": "healthy",
        "service": "api_gateway",
        "file_service": "configured" if config.FILE_SERVICE_URL else "not_configured",
        "orchestrator": "configured" if config.ORCHESTRATOR_URL else "not_configured"
    }


@app.post("/api/process", response_model=UserResponse)
async def process_request(
    user_id: str = Form(..., description="Telegram ID пользователя"),
    text: str = Form(..., description="Текст запроса"),
    files: Optional[List[UploadFile]] = File(None, description="Файлы от пользователя")
):
    """
    Обработка запроса пользователя.
    
    Workflow:
    1. Получение user_id, text, files
    2. Сохранение файлов в File Service
    3. Отправка text + file URLs в Orchestrator
    4. Возврат ответа пользователю
    """
    logger.info(f"Получен запрос от user_id={user_id}")
    warnings = []
    file_urls = []
    
    # Шаг 1: Сохранение файлов
    if files:
        logger.info(f"Обработка {len(files)} файлов")
        file_urls, file_warnings = await save_files_to_service(user_id, files)
        warnings.extend(file_warnings)
    
    # Шаг 2: Отправка в Orchestrator
    response_text, orchestrator_warnings = await send_to_orchestrator(
        user_id=user_id,
        text=text,
        files=file_urls
    )
    warnings.extend(orchestrator_warnings)
    
    # Шаг 3: Формирование ответа
    if response_text is None:
        logger.error(f"Не удалось получить ответ от Orchestrator для user_id={user_id}")
        return UserResponse(
            success=False,
            error="Не удалось обработать запрос",
            warnings=warnings
        )
    
    logger.info(f"Запрос user_id={user_id} успешно обработан")
    return UserResponse(
        success=True,
        response=response_text,
        warnings=warnings if warnings else []
    )


@app.post("/api/stream")
async def stream_request(
    user_id: str = Form(..., description="Telegram ID пользователя"),
    text: str = Form(..., description="Текст запроса"),
    files: Optional[List[UploadFile]] = File(None, description="Файлы от пользователя")
):
    """
    Стриминг ответа от Orchestrator.
    
    Возвращает SSE stream с кусками ответа.
    """
    logger.info(f"Получен stream запрос от user_id={user_id}")
    file_urls = []
    
    # Сохранение файлов (если есть)
    if files:
        logger.info(f"Обработка {len(files)} файлов для стриминга")
        file_urls, warnings = await save_files_to_service(user_id, files)
        
        # Отправляем предупреждения о файлах первым чанком
        if warnings:
            for warning in warnings:
                yield f"data: {{'warning': '{warning}'}}\n\n"
    
    # Стриминг от Orchestrator
    return StreamingResponse(
        stream_from_orchestrator(user_id, text, file_urls),
        media_type="text/event-stream"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=True
    )
