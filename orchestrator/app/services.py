"""Сервисы для взаимодействия с downstream services."""
import httpx
import logging
from typing import List, Optional, AsyncIterator
from .config import config
from .models import FileReference, ProcessedFile, RoutingDecision

logger = logging.getLogger(__name__)


async def extract_text_from_documents(
    user_id: str,
    files: List[FileReference]
) -> List[ProcessedFile]:
    """
    Шаг 1a: Извлечение текста из документов через Tika (file_service).
    
    Обрабатывает: PDF, DOCX, TXT, etc.
    """
    processed = []
    
    # Фильтруем только документы (не изображения/видео)
    document_types = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
        "text/plain",
        "text/markdown",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/octet-stream"
    ]
    
    documents = [f for f in files if f.type in document_types]
    
    if not documents:
        logger.info("No documents to extract")
        return processed
    
    logger.info(f"Extracting text from {len(documents)} documents via Tika")
    
    async with httpx.AsyncClient(timeout=config.TIMEOUT_TIKA) as client:
        for file in documents:
            try:
                # file.url = "/download/123456789/45965963_README.md"
                # file.filename = "123456789/45965963_README.md"
                
                # Используем filename напрямую (он уже в правильном формате)
                response = await client.post(
                    f"{config.FILE_SERVICE_URL}/extract/{file.filename}",  # ⬅️ ИСПРАВЛЕНО
                    headers={"user-id": user_id}
                )
                response.raise_for_status()
                result = response.json()
                
                processed.append(ProcessedFile(
                    filename=file.filename,
                    original_type=file.type,
                    extracted_text=result["text"],
                    processing_method="tika"
                ))
                
                logger.info(f"Extracted {result['length']} chars from {file.filename}")
                
            except Exception as e:
                logger.error(f"Tika extraction failed for {file.filename}: {e}")
                continue
    
    return processed


async def recognize_multimodal_files(
    user_id: str,
    files: List[FileReference]
) -> List[ProcessedFile]:
    """
    Шаг 1b: Распознавание изображений/видео через Qwen3-VL (llm_service).
    
    Обрабатывает: JPG, PNG, GIF, MP4, etc.
    """
    processed = []
    
    # Фильтруем только мультимодальные файлы
    multimodal_types = [
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "video/mp4",
        "video/webm"
    ]
    
    media_files = [f for f in files if f.type in multimodal_types]
    
    if not media_files:
        return processed
    
    logger.info(f"Recognizing {len(media_files)} media files via Qwen3-VL")
    
    async with httpx.AsyncClient(timeout=config.TIMEOUT_LLM_VISION) as client:
        for file in media_files:
            try:
                # Для vision нужен полный URL для скачивания
                file_url = f"{config.FILE_SERVICE_URL}{file.url}"  # ⬅️ ЗДЕСЬ url правильный
                
                response = await client.post(
                    f"{config.LLM_SERVICE_URL}/vision/recognize",
                    json={
                        "user_id": user_id,
                        "file_url": file_url,
                        "file_type": file.type,
                        "prompt": "Опиши подробно что изображено на этом изображении."
                    }
                )
                response.raise_for_status()
                result = response.json()
                
                processed.append(ProcessedFile(
                    filename=file.filename,
                    original_type=file.type,
                    extracted_text=result["description"],
                    processing_method="qwen3vl"
                ))
                
                logger.info(f"Recognized {file.filename}: {len(result['description'])} chars")
                
            except Exception as e:
                logger.error(f"Vision recognition failed for {file.filename}: {e}")
                continue
    
    return processed



async def route_request(
    user_id: str,
    original_prompt: str,
    processed_files: List[ProcessedFile]
) -> RoutingDecision:
    """
    Шаг 2: Роутинг через prompting_service.
    
    Отправляет промпт + распознанные файлы в prompting_service,
    получает enhanced_prompt и решение куда направить (llm/comfy).
    """
    logger.info("Routing request via prompting_service")
    
    # Собираем контекст из обработанных файлов
    files_context = "\n\n".join([
        f"Файл: {f.filename}\nТип: {f.original_type}\nСодержимое:\n{f.extracted_text}"
        for f in processed_files
    ])
    
    async with httpx.AsyncClient(timeout=config.TIMEOUT_PROMPTING) as client:
        try:
            response = await client.post(
                f"{config.PROMPTING_SERVICE_URL}/route",
                json={
                    "user_id": user_id,
                    "user_prompt": original_prompt,
                    "files_context": files_context,
                    "available_routes": ["llm", "comfy"]
                }
            )
            response.raise_for_status()
            result = response.json()
            
            decision = RoutingDecision(**result)
            logger.info(f"Routing decision: {decision.route}, prompt length: {len(decision.enhanced_prompt)}")
            
            return decision
            
        except Exception as e:
            logger.error(f"Prompting service failed: {e}, falling back to LLM")
            # Fallback: отправляем в LLM
            return RoutingDecision(
                route="llm",
                enhanced_prompt=f"{original_prompt}\n\nКонтекст:\n{files_context}",
                reasoning="Prompting service unavailable, fallback to LLM"
            )


async def stream_from_llm(
    user_id: str,
    prompt: str
) -> AsyncIterator[str]:
    """
    Шаг 3a: Стриминг от LLM service.
    """
    logger.info("Streaming from LLM service")
    
    async with httpx.AsyncClient(timeout=config.TIMEOUT_LLM_TEXT) as client:
        async with client.stream(
            "POST",
            f"{config.LLM_SERVICE_URL}/chat/stream",
            json={
                "user_id": user_id,
                "prompt": prompt,
                "stream": True
            }
        ) as response:
            response.raise_for_status()
            
            async for chunk in response.aiter_text():
                if chunk:
                    yield chunk


async def stream_from_comfyui(
    user_id: str,
    prompt: str,
    metadata: Optional[dict] = None
) -> AsyncIterator[str]:
    """
    Шаг 3b: Стриминг от ComfyUI service.
    
    ComfyUI обычно не стримит, поэтому возвращаем статусы + финальное изображение.
    """
    logger.info("Generating image via ComfyUI service")
    
    async with httpx.AsyncClient(timeout=config.TIMEOUT_COMFYUI) as client:
        async with client.stream(
            "POST",
            f"{config.COMFYUI_SERVICE_URL}/generate/stream",
            json={
                "user_id": user_id,
                "prompt": prompt,
                "metadata": metadata or {}
            }
        ) as response:
            response.raise_for_status()
            
            async for chunk in response.aiter_text():
                if chunk:
                    yield chunk
