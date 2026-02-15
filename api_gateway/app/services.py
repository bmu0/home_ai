"""Сервисы для взаимодействия с внешними API."""
import json
import httpx
import logging
from typing import List, Tuple, AsyncIterator
from datetime import datetime
from fastapi import UploadFile

from .config import config
from .models import FileReference, OrchestratorRequest

logger = logging.getLogger(__name__)


def _sse(event: str, data: dict) -> str:
    """Форматирование SSE события."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def save_files_to_service(
    user_id: str,
    files: List[UploadFile]
) -> Tuple[List[FileReference], List[str]]:
    """
    Отправка файлов в File Service.

    Args:
        user_id: ID пользователя
        files: Список загружаемых файлов

    Returns:
        Tuple[список FileReference с URL, список предупреждений]
    """
    warnings = []
    saved_files = []

    if not config.FILE_SERVICE_URL:
        warning = "FILE_SERVICE_URL не настроен, файлы не будут сохранены"    
        logger.warning(warning)
        warnings.append(warning)
        return saved_files, warnings

    async with httpx.AsyncClient(timeout=120.0) as client:
        for file in files:
            try:
                # Сбрасываем позицию файла на начало
                await file.seek(0)
                
                # Читаем весь файл
                content = await file.read()

                # Отправляем в File Service с user_id в HEADER
                response = await client.post(
                    f"{config.FILE_SERVICE_URL}/upload",
                    files={"file": (file.filename, content, file.content_type)},
                    headers={"user-id": user_id}
                )
                response.raise_for_status()

                result = response.json()
                saved_files.append(
                    FileReference(
                        filename=result.get("file_id"),
                        url=result.get("url"),
                        type=file.content_type
                    )
                )

                logger.info(f"Файл {file.filename} успешно сохранен как {result.get('file_id')}")

            except Exception as e:
                warning = f"Ошибка при сохранении файла {file.filename}: {str(e)}"
                logger.error(warning)
                warnings.append(warning)
                continue

    return saved_files, warnings


async def stream_from_orchestrator(
    user_id: str,
    text: str,
    file_refs: List[FileReference]
) -> AsyncIterator[str]:
    """
    Проксирование stream от Orchestrator.
    
    Args:
        user_id: ID пользователя
        text: Текст запроса
        file_refs: Список ссылок на файлы из File Service
        
    Yields:
        SSE-события от Orchestrator
    """
    if not config.ORCHESTRATOR_URL:
        yield _sse("error", {"error": "ORCHESTRATOR_URL не настроен"})
        return
    
    try:
        # Формируем запрос с явной сериализацией FileReference
        request_data = {
            "user_id": user_id,
            "text": text,
            "files": [
                {
                    "filename": f.filename,
                    "url": f.url,
                    "type": f.type
                }
                for f in file_refs
            ]
        }
        
        logger.info(f"Отправка в Orchestrator: {json.dumps(request_data, ensure_ascii=False)}")
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream(
                "POST",
                f"{config.ORCHESTRATOR_URL}/stream",
                json=request_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                response.raise_for_status()
                
                async for chunk in response.aiter_text():
                    if chunk:
                        yield chunk
    
    except Exception as e:
        error = f"Ошибка при стриминге от Orchestrator: {str(e)}"
        logger.error(error)
        yield _sse("error", {"error": error})
