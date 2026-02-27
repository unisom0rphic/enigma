import json
from typing import Dict, List

import requests

from app.config import get_settings

settings = get_settings()

SYSTEM_PROMPT = """
Ты сотрудник службы поддержки газовой службы. 
Твоя задача — проанализировать жалобу и составить ответ.

Входящий текст содержит плейсхолдеры вместо личных данных:
<NAME_1>, <DEVICE_1> и т.д.

ПРАВИЛА ОТВЕТА:
1. Сгенерируй краткое саммари проблемы (summary).
2. Определи тональность жалобы (sentiment): positive, negative или neutral.
3. Напиши вежливый ответ пользователю (answer).
   - В ответе используй плейсхолдеры из входящего текста.
   - Если нужно изменить падеж имени, добавь суффикс падежа к плейсхолдеру: _NOM (кто?), _GEN (кого?), _DAT (кому?), _ACC (кого?), _INS (кем?), _ABL (о ком?).
   - Пример: "Уважаемый <NAME_1_NOM>, мы отправим уведомление для <NAME_1_GEN>".

Верни результат СТРОГО валидным JSON без markdown:
{
  "sentiment": "negative",
  "summary": "Краткое описание...",
  "answer": "Текст ответа..."
}
"""


async def generate_response(masked_text: str, context: List[str]) -> Dict:
    """
    Генерация ответа. Реальный вызов или мок.
    """
    if settings.USE_MOCK_AI:
        return mock_llm_call(masked_text, context)
    else:
        return real_llm_call(masked_text, context)


def mock_llm_call(masked_text: str, context: List[str]) -> Dict:
    """Имитация умной LLM, возвращающая JSON."""

    # Эмулируем анализ
    sentiment = (
        "negative"
        if "сломался" in masked_text or "не работает" in masked_text
        else "neutral"
    )

    # Эмулируем ответ с падежами
    answer = (
        "Здравствуйте, <NAME_1_NOM>! "
        "Мы получили ваше обращение по поводу оборудования <DEVICE_1>. "
        "Для решения проблемы нужно обратиться в сервисный центр. "
        "Мы отправим уведомление для <NAME_1_GEN> по почте."
    )

    summary = "Обращение по поломке <DEVICE_1>. Требуется сервис."

    return {"sentiment": sentiment, "summary": summary, "answer": answer}


def real_llm_call(masked_text: str, context: List[str]) -> Dict:
    """Реальный запрос к HF API."""

    context_str = "\n".join(context)
    full_prompt = (
        f"Контекст из базы знаний:\n{context_str}\n\nЖалоба клиента:\n{masked_text}"
    )

    payload = {
        "inputs": full_prompt,
        "parameters": {
            "return_full_text": False,
            "max_new_tokens": 500,
            "temperature": 0.7,
        },
    }

    headers = {
        "Authorization": f"Bearer {settings.HF_API_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            settings.HF_API_URL, json=payload, headers=headers, timeout=30
        )
        response.raise_for_status()
        result_text = response.json()[0]["generated_text"]

        # Парсим JSON из ответа
        # Иногда LLM любят добавить мусор в начале, пытаемся найти JSON
        start_idx = result_text.find("{")
        end_idx = result_text.rfind("}") + 1
        if start_idx != -1 and end_idx > start_idx:
            json_str = result_text[start_idx:end_idx]
            return json.loads(json_str)
        else:
            return {"error": "Failed to parse LLM JSON", "raw": result_text}

    except Exception as e:
        print(f"LLM Error: {e}")
        return {"error": str(e)}
