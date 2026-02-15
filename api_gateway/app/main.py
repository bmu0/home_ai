"""API Gateway - главный модуль (stream-only).

Эндпоинты:
- GET  /health      — простая проверка
- POST /api/stream  — принимает user_id, text, files; сохраняет файлы; проксирует стрим оркестратора

Важно:
- Возвращаем SSE (text/event-stream).
- Предупреждения (например, файл-сервис недоступен) отправляем первыми SSE-ивентами, затем начинаем
  проксировать чанки от оркестратора.
"""
import json
import logging
from typing import List, Optional, AsyncIterator

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .config import config
from .services import save_files_to_service, stream_from_orchestrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Home AI - API Gateway",
    description="Единая точка входа для всех клиентов системы (stream-only).",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _sse(event: str, data_obj) -> str:
    """Собирает SSE-сообщение: event + data + пустая строка."""
    # SSE требует \n\n в конце сообщения. Форматируем data как JSON, чтобы клиенту было проще.
    return f"event: {event}\n" f"data: {json.dumps(data_obj, ensure_ascii=False)}\n\n"


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "api_gateway",
        "file_service": "configured" if config.FILE_SERVICE_URL else "not_configured",
        "orchestrator": "configured" if config.ORCHESTRATOR_URL else "not_configured",
    }


@app.post("/api/stream")
async def stream_request(
    user_id: str = Form(..., description="Telegram ID пользователя"),
    text: str = Form(..., description="Текст запроса"),
    files: Optional[List[UploadFile]] = File(None, description="Файлы от пользователя"),
):
    """
    Стриминг ответа от Orchestrator (SSE).

    Flow:
    1) (Опционально) отправляем файлы в file-service, получаем ссылки и warnings.
    2) Первый(е) SSE-ивенты: warnings (если есть) + meta (сколько файлов сохранили).
    3) Дальше проксируем stream от orchestrator как есть (ожидаем, что orchestrator тоже отдаёт SSE).
    """

    logger.info("Stream request: user_id=%s, files=%s", user_id, 0 if not files else len(files))

    async def event_generator() -> AsyncIterator[str]:
        file_urls = []
        warnings: List[str] = []

        # 1) Сохранение файлов (ошибки НЕ валят шлюз — просто warning)
        if files:
            file_urls, warnings = await save_files_to_service(user_id, files)

        # 2) Отдаём warnings первыми ивентами
        for w in warnings:
            yield _sse("warning", {"message": w})

        # Можно отправить мета-инфу, чтобы клиент знал, что файлы учтены/не учтены
        yield _sse(
            "meta",
            {"user_id": user_id, "saved_files": len(file_urls), "has_files": bool(files)},
        )

        # 3) Проксируем upstream-стрим оркестратора
        # ВАЖНО: stream_from_orchestrator должен yield-ить уже готовые SSE-чанки (строки с \n\n),
        # либо любые текстовые куски, которые клиент понимает. Мы не буферизуем.
        async for chunk in stream_from_orchestrator(user_id, text, file_urls):
            if chunk:
                yield chunk

    # StreamingResponse принимает (async)generator и держит соединение открытым [web:57].
    return StreamingResponse(event_generator(), media_type="text/event-stream")
