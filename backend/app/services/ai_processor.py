import asyncio

# app/services/ai_processor.py
async def call_external_ai(message: str) -> str:
    # Эмуляция долгого вызова
    await asyncio.sleep(2)
    return "Здравствуйте! Мы уже работаем над вашей проблемой."