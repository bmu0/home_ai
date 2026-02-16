"""Логика стриминга и накопления чанков."""
import logging
from typing import AsyncIterator, Optional
from telegram import Bot

logger = logging.getLogger(__name__)


class StreamAccumulator:
    """
    Накопитель чанков для имитации стриминга в Telegram.
    
    Собирает текст до появления \\n\\n и отправляет сообщением.
    """
    
    def __init__(self, bot: Bot, chat_id: int):
        self.bot = bot
        self.chat_id = chat_id
        self.buffer = ""
        self.current_message_id: Optional[int] = None
    
    async def add_chunk(self, text: str):
        """
        Добавить чанк текста в буфер.
        
        Если буфер содержит \\n\\n — отправляет всё до него сообщением в Telegram.
        """
        self.buffer += text
        
        # Проверяем наличие двойного переноса строки
        if "\n\n" in self.buffer:
            await self._send_buffer()
    
    async def flush(self):
        """Отправить остаток буфера (вызывается в конце стрима)."""
        if self.buffer:
            await self._send_buffer()
    
    async def _send_buffer(self):
        """Отправить текущий буфер в Telegram."""
        if not self.buffer:
            return
        
        # Разбиваем по \\n\\n
        parts = self.buffer.split("\n\n", 1)
        
        # Отправляем первую часть (до \\n\\n или весь буфер если нет \\n\\n)
        text_to_send = parts[0].strip()
        
        if text_to_send:
            try:
                message = await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=text_to_send
                )
                
                logger.info(f"Sent chunk: {len(text_to_send)} chars to chat {self.chat_id}")
                self.current_message_id = message.message_id
            
            except Exception as e:
                logger.error(f"Failed to send message: {e}")
        
        # Оставляем в буфере остаток (после \\n\\n)
        if len(parts) > 1:
            self.buffer = parts[1]
        else:
            self.buffer = ""


async def stream_response_to_telegram(
    bot: Bot,
    chat_id: int,
    sse_stream: AsyncIterator[str]
):
    """
    Обрабатывает SSE stream от API Gateway и отправляет в Telegram.
    
    Отправляет сообщение при появлении \\n\\n в тексте.
    
    Args:
        bot: Telegram Bot instance
        chat_id: ID чата для отправки
        sse_stream: AsyncIterator с SSE событиями
    """
    accumulator = StreamAccumulator(bot, chat_id)
    
    try:
        async for line in sse_stream:
            if not line or line.startswith(":"):
                continue
            
            # Парсим SSE
            if line.startswith("event: "):
                event_type = line[7:].strip()
                continue
            
            if line.startswith("data: "):
                import json
                try:
                    data = json.loads(line[6:])
                    
                    # Обрабатываем разные типы событий
                    if event_type == "response":
                        if data.get("type") == "text":
                            content = data.get("content", "")
                            await accumulator.add_chunk(content)
                        
                        elif data.get("type") == "image":
                            # Отправляем накопленный текст перед картинкой
                            await accumulator.flush()
                            
                            # Отправляем картинку
                            await bot.send_photo(
                                chat_id=chat_id,
                                photo=data.get("url"),
                                caption=data.get("caption")
                            )
                        
                        # Аналогично для других типов
                    
                    elif event_type == "status":
                        # Можно логировать или игнорировать статусы
                        logger.info(f"Status: {data.get('message')}")
                    
                    elif event_type == "error":
                        # Отправляем ошибку пользователю
                        await accumulator.flush()
                        await bot.send_message(
                            chat_id=chat_id,
                            text=f"❌ Ошибка: {data.get('message')}"
                        )
                    
                    elif event_type == "done":
                        # Отправляем остаток буфера
                        await accumulator.flush()
                        logger.info("Stream completed")
                        break
                
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse SSE data: {line}")
                    continue
    
    finally:
        # Убедимся что весь текст отправлен
        await accumulator.flush()
