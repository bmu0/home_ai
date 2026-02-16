"""Обработчики сообщений Telegram."""
import logging
import httpx
from telegram import Update
from telegram.ext import ContextTypes

from .config import config
from .streaming import stream_response_to_telegram

logger = logging.getLogger(__name__)


def check_access(user_id: int) -> bool:
    """Проверка доступа пользователя."""
    if not config.ALLOWED_USER_IDS:
        logger.warning("ALLOWED_USER_IDS не настроен, доступ разрешён всем")
        return True
    
    return user_id in config.ALLOWED_USER_IDS


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start."""
    user_id = update.effective_user.id
    
    if not check_access(user_id):
        await update.message.reply_text("🚫 Доступ запрещён")
        logger.warning(f"Access denied for user {user_id}")
        return
    
    await update.message.reply_text(
        "👋 Привет! Я AI ассистент.\n\n"
        "Отправь мне текст или файлы, и я их обработаю."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Главный обработчик сообщений.
    
    Собирает текст + файлы и отправляет в API Gateway.
    """
    user_id = update.effective_user.id
    
    # Проверка доступа
    if not check_access(user_id):
        await update.message.reply_text("🚫 Доступ запрещён")
        logger.warning(f"Access denied for user {user_id}")
        return
    
    message = update.message
    
    # Собираем текст
    text = message.text or message.caption or ""
    
    if not text and not message.document and not message.photo:
        await message.reply_text("❓ Отправьте текст или файл")
        return
    
    # Собираем файлы
    files = []
    
    # Документы
    if message.document:
        file = await message.document.get_file()
        file_bytes = await file.download_as_bytearray()
        files.append({
            "filename": message.document.file_name,
            "content": bytes(file_bytes),
            "mime_type": message.document.mime_type
        })
    
    # Фото (берём максимальное разрешение)
    if message.photo:
        photo = message.photo[-1]
        file = await photo.get_file()
        file_bytes = await file.download_as_bytearray()
        files.append({
            "filename": f"photo_{photo.file_id}.jpg",
            "content": bytes(file_bytes),
            "mime_type": "image/jpeg"
        })
    
    # Отправляем запрос в API Gateway
    await send_to_gateway(message, user_id, text, files)


async def send_to_gateway(message, user_id: int, text: str, files: list):
    """
    Отправка запроса в API Gateway и стриминг ответа в Telegram.
    """
    logger.info(f"Processing message from {user_id}: text={len(text)} chars, files={len(files)}")
    
    # Уведомляем пользователя
    status_msg = await message.reply_text("⏳ Обрабатываю запрос...")
    
    try:
        # Формируем multipart/form-data
        data = {
            "user_id": str(user_id),
            "text": text
        }
        
        files_data = []
        for f in files:
            files_data.append(
                ("files", (f["filename"], f["content"], f["mime_type"]))
            )
        
        # Отправляем запрос с SSE стримом
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream(
                "POST",
                f"{config.API_GATEWAY_URL}/api/stream",
                data=data,
                files=files_data if files_data else None,
                headers={"Accept": "text/event-stream"}
            ) as response:
                response.raise_for_status()
                
                # Удаляем статусное сообщение
                await status_msg.delete()
                
                # Стримим ответ в Telegram
                await stream_response_to_telegram(
                    bot=message.get_bot(),
                    chat_id=message.chat_id,
                    sse_stream=response.aiter_lines(),
                )
    
    except httpx.HTTPError as e:
        logger.error(f"API Gateway error: {e}")
        await status_msg.edit_text(f"❌ Ошибка API: {e}")
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        await status_msg.edit_text(f"❌ Ошибка: {e}")
