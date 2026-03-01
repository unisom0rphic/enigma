# app/main.py
import asyncio
import logging
from contextlib import asynccontextmanager

# Новые импорты
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.endpoints import router as tickets_router
from app.bot.listener import listen_redis
from app.config import settings
from app.db.database import create_db_pool, init_db
from app.db.repository import MessageRepository
from app.workers.email_watcher import email_polling_worker

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    logger.info("Starting up...")

    # 1. База данных
    pool = await create_db_pool()
    await init_db(pool)
    app.state.db_pool = pool
    repo = MessageRepository(pool)

    # 2. Воркер почты
    email_task = asyncio.create_task(email_polling_worker(repo))

    # 3. Telegram Bot
    bot_task = None
    bot = None

    if settings.TELEGRAM_BOT_TOKEN:
        bot = Bot(
            token=settings.TELEGRAM_BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        bot_task = asyncio.create_task(listen_redis(bot))
    else:
        logger.warning("TELEGRAM_BOT_TOKEN not set. Bot disabled.")

    yield

    # --- Shutdown ---
    logger.info("Shutting down...")

    email_task.cancel()
    if bot_task:
        bot_task.cancel()

    try:
        await email_task
    except asyncio.CancelledError:
        pass

    if bot_task:
        try:
            await bot_task
        except asyncio.CancelledError:
            pass

    if bot:
        await bot.session.close()

    await pool.close()


app = FastAPI(title="AI Support Backend", lifespan=lifespan)


app.include_router(tickets_router, prefix="/api/v1")

origins = [
    "http://localhost:5173",  # Стандартный адрес SvelteKit / Vite
    "http://localhost:3000",  # Если используете другой порт
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Разрешает запросы с этих адресов
    allow_credentials=True,  # Разрешает куки и заголовки авторизации
    allow_methods=["*"],  # Разрешает все методы (GET, POST, PUT, DELETE)
    allow_headers=["*"],  # Разрешает все заголовки
)
