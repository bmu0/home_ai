"""Сервисы для работы с llama.cpp."""
import httpx
import json
import logging
from typing import AsyncIterator, List, Optional
from .config import config
from .models import Message, ChatRequest, VisionRequest, VisionResponse

logger = logging.getLogger(__name__)


def _sse(event: str, data: dict) -> str:
    """Форматирование SSE события."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def stream_chat(request: ChatRequest) -> AsyncIterator[str]:
    """
    Стриминг ответа от llama.cpp через OpenAI-compatible API.
    
    Использует /v1/chat/completions endpoint.
    """
    logger.info(f"Chat request from {request.user_id}, prompt length: {len(request.prompt)}")
    
    # Формируем messages для OpenAI API
    messages = []
    
    # Системный промпт (если есть)
    if request.system_prompt:
        messages.append({
            "role": "system",
            "content": request.system_prompt
        })
    
    # Если переданы готовые messages, используем их
    if request.messages:
        messages.extend([
            {"role": msg.role, "content": msg.content}
            for msg in request.messages
        ])
    else:
        # Иначе создаём одно user-сообщение
        messages.append({
            "role": "user",
            "content": request.prompt
        })
    
    # Параметры генерации
    payload = {
        "model": config.MODEL_NAME,
        "messages": messages,
        "stream": True,
        "temperature": request.temperature or config.DEFAULT_TEMPERATURE,
        "max_tokens": request.max_tokens or config.DEFAULT_MAX_TOKENS,
        "top_p": request.top_p or config.DEFAULT_TOP_P
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    if config.LLAMA_CPP_API_KEY:
        headers["Authorization"] = f"Bearer {config.LLAMA_CPP_API_KEY}"
    
    try:
        async with httpx.AsyncClient(timeout=config.TIMEOUT_CHAT) as client:
            async with client.stream(
                "POST",
                f"{config.LLAMA_CPP_URL}/v1/chat/completions",
                json=payload,
                headers=headers
            ) as response:
                response.raise_for_status()
                
                # Парсим SSE stream от llama.cpp
                async for line in response.aiter_lines():
                    if not line or line.startswith(":"):
                        continue
                    
                    # Убираем "data: " префикс
                    if line.startswith("data: "):
                        line = line[6:]
                    
                    # Пропускаем [DONE]
                    if line.strip() == "[DONE]":
                        break
                    
                    try:
                        chunk = json.loads(line)
                        
                        # Извлекаем текст из delta
                        if "choices" in chunk and len(chunk["choices"]) > 0:
                            delta = chunk["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            
                            if content:
                                yield _sse("response", {
                                    "type": "text",
                                    "content": content
                                })
                    
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse chunk: {line}")
                        continue
    
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error from llama.cpp: {e}")
        yield _sse("error", {
            "message": f"LLM service error: {e.response.status_code}"
        })
    
    except Exception as e:
        logger.error(f"Chat streaming error: {e}")
        yield _sse("error", {
            "message": f"Ошибка генерации: {str(e)}"
        })
    
    # Финальный событие
    yield _sse("done", {"status": "completed"})


async def recognize_vision(request: VisionRequest) -> VisionResponse:
    """
    Распознавание изображения через Qwen3-VL (llama.cpp with mmproj).
    
    Использует /v1/chat/completions с image_url в content.
    """
    logger.info(f"Vision request from {request.user_id}: {request.file_url}")
    
    # Формируем запрос с изображением
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": request.prompt
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": request.file_url,
                        "detail": request.detail or config.VISION_DETAIL
                    }
                }
            ]
        }
    ]
    
    payload = {
        "model": config.MODEL_NAME,
        "messages": messages,
        "stream": False,  # Не стримим для vision
        "temperature": 0.3,  # Низкая температура для точности
        "max_tokens": 1024
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    if config.LLAMA_CPP_API_KEY:
        headers["Authorization"] = f"Bearer {config.LLAMA_CPP_API_KEY}"
    
    try:
        async with httpx.AsyncClient(timeout=config.TIMEOUT_VISION) as client:
            response = await client.post(
                f"{config.LLAMA_CPP_URL}/v1/chat/completions",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            result = response.json()
            
            # Извлекаем описание из ответа
            description = result["choices"][0]["message"]["content"]
            
            logger.info(f"Vision recognition successful: {len(description)} chars")
            
            return VisionResponse(
                description=description,
                confidence=1.0,
                metadata={
                    "model": result.get("model"),
                    "tokens_used": result.get("usage", {}).get("total_tokens")
                }
            )
    
    except Exception as e:
        logger.error(f"Vision recognition error: {e}")
        raise
