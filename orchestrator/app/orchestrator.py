"""Основная логика оркестрации."""
import json
import asyncio
import logging
from typing import AsyncIterator, List
from .models import IncomingRequest, ProcessedFile
from .services import (
    extract_text_from_documents,
    recognize_multimodal_files,
    route_request,
    stream_from_llm,
    stream_from_comfyui
)

logger = logging.getLogger(__name__)


def _sse(event: str, data: dict) -> str:
    """Форматирование SSE события."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def orchestrate_request(request: IncomingRequest) -> AsyncIterator[str]:
    """
    Главная функция оркестрации.
    
    Шаг 1: Параллельная обработка файлов (Tika + Qwen3-VL)
    Шаг 2: Роутинг через prompting_service
    Шаг 3: Выполнение запроса (LLM или ComfyUI) + стриминг
    """
    
    # === ШАГ 1: Обработка файлов (параллельно) ===
    processed_files: List[ProcessedFile] = []
    
    if request.files:
        yield _sse("status", {
            "message": f"Обрабатываю {len(request.files)} файлов...",
            "step": "file_processing"
        })
        
        try:
            # Запускаем Tika и Qwen3-VL параллельно
            tika_task = extract_text_from_documents(request.user_id, request.files)
            vision_task = recognize_multimodal_files(request.user_id, request.files)
            
            tika_results, vision_results = await asyncio.gather(
                tika_task,
                vision_task,
                return_exceptions=True
            )
            
            # Обработка результатов
            if isinstance(tika_results, list):
                processed_files.extend(tika_results)
            else:
                logger.error(f"Tika processing error: {tika_results}")
            
            if isinstance(vision_results, list):
                processed_files.extend(vision_results)
            else:
                logger.error(f"Vision processing error: {vision_results}")
            
            if processed_files:
                yield _sse("status", {
                    "message": f"Обработано файлов: {len(processed_files)}",
                    "step": "file_processing_complete",
                    "files": [f.filename for f in processed_files]
                })
        
        except Exception as e:
            logger.error(f"File processing error: {e}")
            yield _sse("warning", {
                "message": f"Ошибка обработки файлов: {str(e)}"
            })
    
    # === ШАГ 2: Роутинг ===
    yield _sse("status", {
        "message": "Определяю маршрут запроса...",
        "step": "routing"
    })
    
    try:
        routing_decision = await route_request(
            request.user_id,
            request.text,
            processed_files
        )
        
        yield _sse("status", {
            "message": f"Маршрут: {routing_decision.route.upper()}",
            "step": "routing_complete",
            "route": routing_decision.route,
            "reasoning": routing_decision.reasoning
        })
    
    except Exception as e:
        logger.error(f"Routing error: {e}")
        yield _sse("error", {
            "message": f"Ошибка роутинга: {str(e)}"
        })
        return
    
    # === ШАГ 3: Выполнение запроса ===
    try:
        if routing_decision.route == "llm":
            # Стримим от LLM
            async for chunk in stream_from_llm(
                request.user_id,
                routing_decision.enhanced_prompt
            ):
                yield chunk
        
        elif routing_decision.route == "comfy":
            # Стримим от ComfyUI
            async for chunk in stream_from_comfyui(
                request.user_id,
                routing_decision.enhanced_prompt,
                routing_decision.metadata
            ):
                yield chunk
        
        else:
            yield _sse("error", {
                "message": f"Неизвестный маршрут: {routing_decision.route}"
            })
    
    except Exception as e:
        logger.error(f"Execution error: {e}")
        yield _sse("error", {
            "message": f"Ошибка выполнения: {str(e)}"
        })
    
    # Завершение
    yield _sse("done", {"status": "completed"})
