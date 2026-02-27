# app/db/database.py
import asyncpg
from app.config import settings

async def create_db_pool():
    return await asyncpg.create_pool(
        dsn=str(settings.POSTGRES_DSN),
        min_size=5,
        max_size=20,
        command_timeout=60,
    )