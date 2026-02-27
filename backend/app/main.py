# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
import asyncio
from app.api.v1.endpoints import router as tickets_router
from app.db.database import create_db_pool
from app.db.repository import MessageRepository
from app.workers.email_watcher import email_polling_worker

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    pool = await create_db_pool()
    app.state.db_pool = pool
    repo = MessageRepository(pool)
    # Запускаем фоновую задачу поллинга
    task = asyncio.create_task(email_polling_worker(repo))
    yield
    # Shutdown
    task.cancel()
    await pool.close()

app = FastAPI(title="AI Support Backend", lifespan=lifespan)
app.include_router(tickets_router, prefix="/api/v1")