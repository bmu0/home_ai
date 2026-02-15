"""Orchestrator Service API."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from .config import config
from .models import IncomingRequest
from .orchestrator import orchestrate_request

# Настройка логирования
logging.basicConfig(
    level=config.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle: startup и shutdown."""
    logger.info("Orchestrator запущен")
    logger.info(f"File Service: {config.FILE_SERVICE_URL}")
    logger.info(f"LLM Service: {config.LLM_SERVICE_URL}")
    logger.info(f"ComfyUI Service: {config.COMFYUI_SERVICE_URL}")
    logger.info(f"Prompting Service: {config.PROMPTING_SERVICE_URL}")
    yield
    logger.info("Orchestrator остановлен")


app = FastAPI(
    title="Home AI - Orchestrator",
    description="Центральный оркестратор для управления запросами",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check."""
    return {
        "status": "healthy",
        "service": "orchestrator",
        "version": "1.0.0"
    }


@app.post("/stream")
async def stream_response(request: IncomingRequest):
    """
    Главный endpoint для оркестрации запроса.
    
    1. Обрабатывает файлы (Tika + Qwen3-VL)
    2. Роутит запрос (prompting_service)
    3. Выполняет и стримит результат (LLM или ComfyUI)
    """
    logger.info(
        f"Stream request: user_id={request.user_id}, "
        f"text='{request.text[:50]}...', files={len(request.files)}"
    )
    
    return StreamingResponse(
        orchestrate_request(request),
        media_type="text/event-stream"
    )
