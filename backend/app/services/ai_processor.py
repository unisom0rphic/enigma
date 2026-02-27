# app/services/ai_processor.py
import asyncio


async def call_external_ai(message: str) -> str:
    # Эмуляция долгого вызова
    await asyncio.sleep(2)
    return "Здравствуйте! Мы уже работаем над вашей проблемой."
