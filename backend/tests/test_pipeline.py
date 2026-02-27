import asyncio
import json
import os
import sys

# --- НАСТРОЙКА ПУТЕЙ ---
# Получаем путь к папке backend (корневая папка проекта для python)
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)
# -----------------------

# ИМПОРТЫ С УЧЕТОМ СТРУКТУРЫ app/services
from app.services.parsing.ner_extractor import extract_entities
from app.services.parsing.utils import mask_pii, unmask_pii
from services.ai_processor_orig import generate_response


# Мок RAG Engine
class MockRAG:
    def get_context(self, text, k=1):
        return ["Инструкция: Газоанализатор ГН-XXXXX требует замены батареи."]


async def main():
    print(f"--- Запуск теста (Backend Dir: {BACKEND_DIR}) ---\n")

    # 1. Сырой Email
    raw_email = """
    Добрый день.
    Пишет вам Иванов Иван.
    У нас сломался газоанализатор ГН-12345, вообще не включается.
    Я очень недоволен качеством!
    Мой телефон +79001234567.
    """

    print(f"1. RAW EMAIL:\n{raw_email.strip()}\n")

    # 2. Извлечение сущностей
    entities = extract_entities(raw_email)
    print("2. EXTRACTED ENTITIES:")
    for e in entities:
        print(f"   - {e}")
    print()

    # 3. Маскировка
    masked_text, entity_map = mask_pii(raw_email, entities)
    print(f"3. MASKED TEXT:\n{masked_text.strip()}\n")

    # 4. RAG
    rag = MockRAG()
    context = rag.get_context(masked_text)

    # 5. AI Generation (Mock LLM)
    llm_response = await generate_response(masked_text, context)
    print(
        f"4. LLM RESPONSE:\n{json.dumps(llm_response, indent=4, ensure_ascii=False)}\n"
    )

    # 6. Демаскировка
    final_answer = unmask_pii(llm_response.get("answer", ""), entity_map)
    print(f"5. FINAL ANSWER:\n{final_answer}\n")


if __name__ == "__main__":
    asyncio.run(main())
