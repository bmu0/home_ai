"""Сервисы для взаимодействия с внешними API."""
import httpx
import logging
from typing import List, Dict, Tuple
from datetime import datetime
from fastapi import UploadFile

from .config import config
from .models import FileUploadResponse, OrchestratorRequest

logger = logging.getLogger(__name__)


async def save_files_to_service(
    user_id: str,
    files: List[UploadFile]
) -> Tuple[List[Dict[str, str]], List[str]]:
    """
    Отправка файлов в File Service.
    
    Args:
        user_id: ID пользователя
        files: Список загружаемых файлов
        
    Returns:
        Tuple[список ссылок на файлы, список предупреждений]
    """
    warnings = []
    saved_files = []
    
    if not config.FILE_SERVICE_URL:
        warning = "FILE_SERVICE_URL не настроен, файлы не будут сохранены"
        logger.warning(warning)
        warnings.append(warning)
        return saved_files, warnings
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    for file in files:
        try:
            # Формируем имя файла с таймштампом
            filename = f"{user_id}_{timestamp}_{file.filename}"
            
            # Читаем содержимое файла
            content = await file.read()
            
            # Отправляем в File Service
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{config.FILE_SERVICE_URL}/upload",
                    files={"file": (filename, content, file.content_type)},
                    data={"user_id": user_id}
                )
                response.raise_for_status()
                
                result = response.json()
                saved_files.append({
                    "filename": filename,
                    "url": result.get("url"),
                    "type": file.content_type
                })
                
                logger.info(f"Файл {filename} успешно сохранен")
                
        except Exception as e:
            warning = f"Ошибка при сохранении файла {file.filename}: {str(e)}"
            logger.error(warning)
            warnings.append(warning)
            continue
    
    return saved_files, warnings


async def send_to_orchestrator(
    user_id: str,
    text: str,
    files: List[Dict[str, str]]
) -> Tuple[str, List[str]]:
    """
    Отправка запроса в Orchestrator.
    
    Args:
        user_id: ID пользователя
        text: Текст запроса
        files: Список ссылок на файлы
        
    Returns:
        Tuple[ответ от оркестратора, список предупреждений]
    """
    warnings = []
    
    if not config.ORCHESTRATOR_URL:
        error = "ORCHESTRATOR_URL не настроен"
        logger.error(error)
        return None, [error]
    
    try:
        request_data = OrchestratorRequest(
            user_id=user_id,
            text=text,
            files=files
        )
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{config.ORCHESTRATOR_URL}/process",
                json=request_data.model_dump()
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get("response"), warnings
            
    except Exception as e:
        error = f"Ошибка при обращении к Orchestrator: {str(e)}"
        logger.error(error)
        return None, [error]


async def stream_from_orchestrator(
    user_id: str,
    text: str,
    files: List[Dict[str, str]]
):
    """
    Стриминг ответа от Orchestrator.
    
    Args:
        user_id: ID пользователя
        text: Текст запроса
        files: Список ссылок на файлы
        
    Yields:
        Куски ответа от оркестратора
    """
    if not config.ORCHESTRATOR_URL:
        yield f"data: {{'error': 'ORCHESTRATOR_URL не настроен'}}\n\n"
        return
    
    try:
        request_data = OrchestratorRequest(
            user_id=user_id,
            text=text,
            files=files
        )
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream(
                "POST",
                f"{config.ORCHESTRATOR_URL}/stream",
                json=request_data.model_dump()
            ) as response:
                response.raise_for_status()
                
                async for chunk in response.aiter_text():
                    if chunk:
                        yield chunk
                        
    except Exception as e:
        error = f"Ошибка при стриминге от Orchestrator: {str(e)}"
        logger.error(error)
        yield f"data: {{'error': '{error}'}}\n\n"
