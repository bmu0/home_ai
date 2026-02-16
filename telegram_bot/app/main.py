"""Главный файл Telegram бота."""
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from .config import config
from .handlers import start_command, handle_message

# Настройка логирования
logging.basicConfig(
    level=config.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Запуск бота."""
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN не установлен в .env")
        return
    
    if not config.ALLOWED_USER_IDS:
        logger.warning("ALLOWED_USER_IDS не установлен, доступ разрешён всем")
    else:
        logger.info(f"Allowed users: {config.ALLOWED_USER_IDS}")
    
    # Создаём приложение
    app = Application.builder().token(config.BOT_TOKEN).build()
    
    # Регистрируем обработчики
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(
        filters.TEXT | filters.PHOTO | filters.Document.ALL,
        handle_message
    ))
    
    # Запускаем бота
    logger.info("Telegram bot запущен")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
