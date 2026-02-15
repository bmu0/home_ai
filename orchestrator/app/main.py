"""Orchestrator - заглушка для тестирования."""
import json
import logging
import asyncio
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from .config import config
from .models import IncomingRequest, ResponseChunk

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Home AI - Orchestrator",
    description="Оркестратор запросов (заглушка)",
    version="0.1.0",
)


def _sse(event: str, data_obj: dict) -> str:
    """Формирует SSE-событие."""
    return f"event: {event}\ndata: {json.dumps(data_obj, ensure_ascii=False)}\n\n"


@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса."""
    return {
        "status": "healthy",
        "service": "orchestrator",
        "version": "0.1.0"
    }


@app.post("/stream")
async def stream_response(request: IncomingRequest):
    """
    Стриминг ответа клиенту (заглушка).
    
    Принимает запрос от Gateway, возвращает SSE-стрим с простым ответом.
    """
    logger.info(
        "Stream request: user_id=%s, text='%s', files=%d",
        request.user_id,
        request.text[:50],
        len(request.files)
    )
    
    async def event_generator() -> AsyncIterator[str]:
        # Имитация обработки (задержка)
        await asyncio.sleep(0.5)
        
        # Формируем ответ
        files_info = f"{len(request.files)} файлов" if request.files else "без файлов"
        response_text = f"Это ответ от оркестратора. В запросе пришло {files_info}."
        
        # Если есть файлы, добавляем детали
        if request.files:
            response_text += "\n\nПолученные файлы:"
            for i, file in enumerate(request.files, 1):
                response_text += f"\n{i}. {file.filename} ({file.type})"
        
        # Отправляем как текстовый ответ
        yield _sse("response", {
            "type": "text",
            "content": response_text
        })
        
        # Имитация второго чанка (опционально)
        await asyncio.sleep(0.3)
        yield _sse("response", {
            "type": "text",
            "content": f"\n\nЗапрос от user_id: {request.user_id}"
        })
        
        # Сигнал завершения
        yield _sse("done", {"status": "completed"})
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
