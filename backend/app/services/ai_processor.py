# app/services/ai_processor.py
import json
from typing import Dict, Optional
from urllib.parse import urlparse

import httpx

from app.config import get_settings

settings = get_settings()

PROMPT_GENERATE_ANSWER = """
Ты сотрудник службы поддержки газовой службы. 
Твоя задача — проанализировать жалобу и подготовить ответ.

Входящий текст содержит плейсхолдеры: <NAME_1>, <DEVICE_1> и т.д.

ПРАВИЛА:
1. summary: Краткое описание проблемы (1 предложение).
2. category: Классифицируй обращение. Варианты: "неисправность", "калибровка", "документация", "консультация", "спам", "благодарность".
3. important: true (если утечка газа, угроза безопасности, взрыв, "срочно") ИНАЧЕ false.
4. sentiment: positive, negative или neutral.
5. answer: Вежливый ответ. Используй плейсхолдеры. Для смены падежа имени добавь суффикс: _GEN (кого?), _DAT (кому?) и т.д.

Верни результат СТРОГО валидным JSON без markdown:
{
  "sentiment": "negative",
  "category": "неисправность",
  "important": false,
  "summary": "Описание...",
  "answer": "Текст ответа..."
}
"""


def _manual_response(reason: str, important: bool = False) -> Dict:
    return {
        "sentiment": "neutral",
        "category": "ошибка обработки",
        "important": important,
        "summary": reason,
        "answer": None,
        "manual_required": True,
    }


def _normalize_hf_url(url: str) -> Optional[str]:
    """
    Нормализует HF API URL: поддерживает старый/новый формат и просто model_id.
    Возвращает None, если URL невалиден.
    """
    if not url or not url.strip():
        return None

    url = url.strip()

    # Если передан только model_id (например, "meta-llama/Meta-Llama-3.1-8B-Instruct")
    if "/" in url and not url.startswith("http"):
        return f"https://router.huggingface.co/hf-inference/models/{url}"

    # Если старый формат api-inference.huggingface.co
    if "api-inference.huggingface.co" in url and "/models/" in url:
        model_id = url.split("/models/")[-1].split("?")[0].strip()
        if model_id:
            return f"https://router.huggingface.co/hf-inference/models/{model_id}"

    # Проверяем, что URL имеет правильный протокол
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return None

    return url


async def _call_llm(
    prompt: str, input_text: str, client: httpx.AsyncClient
) -> Optional[dict]:
    full_prompt = f"{prompt}\n\nТекст:\n{input_text}"
    payload = {
        "inputs": full_prompt,
        "parameters": {
            "return_full_text": False,
            "max_new_tokens": 300,
            "temperature": 0.1,
        },
    }
    # Внутри _call_llm, самая первая строка:
    import re

    raw_url = getattr(settings, "HF_API_URL", "").strip()
    # Удаляем ВСЕ пробельные символы (включая \t, \n, \r)
    settings.HF_API_URL = re.sub(r"\s+", "", raw_url)

    # Нормализуем и валидируем URL
    api_url = _normalize_hf_url(settings.HF_API_URL)
    if not api_url:
        print(
            f"LLM Error: Неверный HF_API_URL='{settings.HF_API_URL}'. "
            f"Ожидается: полный URL или model_id (напр. 'meta-llama/Meta-Llama-3.1-8B-Instruct')"
        )
        return None

    headers = {"Authorization": f"Bearer {settings.HF_API_TOKEN}"}

    try:
        api_url = settings.HF_API_URL.strip().rstrip(
            "/"
        )  # убираем лишние пробелы/слеши
        if not api_url.startswith("http"):
            api_url = f"https://router.huggingface.co/hf-inference/models/{api_url}"
        response = await client.post(
            api_url, json=payload, headers=headers, timeout=30.0
        )
        response.raise_for_status()
        result_text = response.json()[0]["generated_text"]
        # Простой парсер JSON (без изменений)
        start_idx = result_text.find("{")
        end_idx = result_text.rfind("}") + 1
        if start_idx != -1 and end_idx > start_idx:
            return json.loads(result_text[start_idx:end_idx])
        return None
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 410:
            print(
                "LLM Error: 410 Gone — эндпоинт устарел. Используйте router.huggingface.co"
            )
        elif e.response.status_code == 401:
            print(
                "LLM Error: 401 Unauthorized — проверьте HF_API_TOKEN и доступ к модели"
            )
        elif e.response.status_code == 404:
            print(
                f"LLM Error: 404 Not Found — модель '{settings.HF_API_URL}' не найдена"
            )
        else:
            print(f"LLM Error: HTTP {e.response.status_code} — {e}")
        return None
    except Exception as e:
        print(f"LLM Error: {e}")
        return None


async def process_ticket_ai(masked_text: str, device_name: Optional[str]) -> Dict:
    """
    Главная точка входа.
    Возвращает словарь с полями: summary, answer, sentiment, category, important, manual_required.
    """

    if not settings.USE_MOCK_AI:
        async with httpx.AsyncClient() as client:
            # Логика RAG / Fetcher (упрощенно)
            pass

    # Генерация ответа
    if settings.USE_MOCK_AI:
        return mock_llm_call(masked_text)

    async with httpx.AsyncClient() as client:
        result = await _call_llm(PROMPT_GENERATE_ANSWER, masked_text, client)
        if result:
            result["manual_required"] = False
            result["important"] = result.get("important", False)
            return result
        else:
            return _manual_response("Ошибка генерации ответа AI")


def mock_llm_call(masked_text: str) -> Dict:
    is_spam = "спам" in masked_text.lower() or "реклама" in masked_text.lower()
    is_urgent = "срочно" in masked_text.lower() or "утечка" in masked_text.lower()

    return {
        "sentiment": "neutral" if is_spam else "negative",
        "category": "спам" if is_spam else "неисправность",
        "important": is_urgent,
        "summary": "Mock summary: анализ текста завершен.",
        "answer": "Mock answer: Уважаемый <NAME_1_NOM>, ваш запрос принят.",
        "manual_required": False,
    }
