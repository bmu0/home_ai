"""LLM Service API."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from .config import config
from .models import ChatRequest, VisionRequest
from .services import stream_chat, recognize_vision

# Настройка логирования
logging.basicConfig(
    level=config.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle: startup и shutdown."""
    logger.info("LLM Service запущен")
    logger.info(f"llama.cpp URL: {config.LLAMA_CPP_URL}")
    logger.info(f"Model: {config.MODEL_NAME}")
    yield
    logger.info("LLM Service остановлен")


app = FastAPI(
    title="LLM Service",
    description="Сервис для работы с Qwen3-VL через llama.cpp",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health():
    """Health check."""
    return {
        "status": "ok",
        "service": "llm_service",
        "llama_cpp_url": config.LLAMA_CPP_URL
    }


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Стриминг генерации текста от LLM.
    
    - Принимает prompt или список messages
    - Стримит ответ через SSE
    - Поддерживает настройку temperature, max_tokens, top_p
    """
    logger.info(f"Chat stream request from {request.user_id}")
    
    return StreamingResponse(
        stream_chat(request),
        media_type="text/event-stream"
    )


@app.post("/vision/recognize")
async def vision_recognize(request: VisionRequest):
    """
    Распознавание изображения через Qwen3-VL.
    
    - Принимает URL изображения
    - Возвращает текстовое описание
    - Не стримит (single response)
    """
    logger.info(f"Vision request from {request.user_id}: {request.file_url}")
    
    try:
        result = await recognize_vision(request)
        return result
    
    except Exception as e:
        logger.error(f"Vision recognition failed: {e}")
        raise HTTPException(500, f"Ошибка распознавания: {str(e)}")
