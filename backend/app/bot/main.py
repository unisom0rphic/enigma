from contextlib import asynccontextmanager
from fastapi import FastAPI
import asyncio
import logging

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.api.v1.endpoints import router as tickets_router
from app.db.database import create_db_pool
from app.db.repository import MessageRepository
from app.workers.email_watcher import email_polling_worker
from app.bot.listener import listen_redis  # Импорт нашей новой функции
from app.config import settings           # Импорт настроек

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    
    # 1. Инициализация БД
    logger.info("Initializing Database Pool...")
    pool = await create_db_pool()
    app.state.db_pool = pool
    repo = MessageRepository(pool)
    
    # 2. Запуск Email Worker (существующая логика)
    logger.info("Starting Email Polling Worker...")
    email_task = asyncio.create_task(email_polling_worker(repo))
    
    # 3. Инициализация Telegram Bot
    logger.info("Initializing Telegram Bot...")
    bot = Bot(
        token=settings.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # 4. Запуск Redis Listener (новая логика)
    logger.info("Starting Redis Listener...")
    bot_task = asyncio.create_task(listen_redis(bot))

    logger.info("Application startup complete.")

    yield
    
    # --- Shutdown ---
    logger.info("Shutting down services...")
    
    # Отменяем фоновые задачи
    email_task.cancel()
    bot_task.cancel()
    
    # Ждем завершения задач (обработка CancelledError)
    try:
        await email_task
    except asyncio.CancelledError:
        pass
        
    try:
        await bot_task
    except asyncio.CancelledError:
        pass

    # Закрываем ресурсы
    await bot.session.close()
    await pool.close()
    
    logger.info("Application shutdown complete.")

# Создание приложения
app = FastAPI(title="AI Support Backend", lifespan=lifespan)

# Подключение роутов
app.include_router(tickets_router, prefix="/api/v1")F