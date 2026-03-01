# backend/app/db/database.py
import logging

import asyncpg

from app.config import settings

logger = logging.getLogger(__name__)


async def create_db_pool():
    # Создаем пул соединений
    pool = await asyncpg.create_pool(
        dsn=str(settings.POSTGRES_DSN),
        min_size=5,
        max_size=20,
        command_timeout=60,
    )
    return pool


async def init_db(pool):
    """
    Создает таблицу, если она не существует.
    Вызывается один раз при старте приложения.
    """
    async with pool.acquire() as conn:
        # Включаем расширение для UUID (стандартная процедура для Postgres)
        await conn.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')

        # SQL запрос на создание таблицы
        create_table_query = """
        CREATE TABLE IF NOT EXISTS tickets (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            created_at TIMESTAMPTZ DEFAULT NOW(),
            
            -- Данные клиента
            full_name TEXT,
            phone_num TEXT,
            email TEXT,
            object_name TEXT, 
            device_type TEXT,
            device_num TEXT,
            
            -- Контент
            original_message TEXT,
            summary TEXT,
            llm_response TEXT,
            
            -- Мета-данные
            sentiment TEXT,
            category TEXT,
            
            -- Флаги
            is_resolved BOOLEAN DEFAULT FALSE,
            is_important BOOLEAN DEFAULT FALSE,
            manual_required BOOLEAN DEFAULT FALSE,
            is_relevant BOOLEAN DEFAULT TRUE
        );
        """

        await conn.execute(create_table_query)
        logger.info("Database table 'tickets' checked/created successfully.")
