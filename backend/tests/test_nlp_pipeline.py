import asyncio
import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

# ---
# 1. Блокировка тяжелых библиотек
# ---
sys.modules["sentence_transformers"] = MagicMock()
sys.modules["faiss"] = MagicMock()
sys.modules["pypdf"] = MagicMock()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---
# 2. Конфигурация и Моки
# ---
mock_settings = MagicMock()
mock_settings.USE_MOCK_AI = False
mock_settings.HF_API_TOKEN = "fake_token"
mock_settings.HF_API_URL = "http://fake-llm-api/api"
mock_settings.DATA_DIR = "data"


def get_llm_response_mock(text):
    resp = MagicMock()
    resp.json.return_value = [
        {
            "generated_text": json.dumps(
                {
                    "sentiment": "neutral",
                    "summary": f"Processed: {text[:30]}...",
                    "answer": f"Получено: {text}",
                }
            )
        }
    ]
    resp.raise_for_status = MagicMock()
    return resp


mock_client = AsyncMock()
mock_client.__aenter__.return_value = mock_client
fake_pdf_path = "/fake/path.pdf"
fake_context = ["Context data"]

# ---
# 3. ТЕСТОВЫЕ СЦЕНАРИИ
# ---
test_cases = [
    {
        "name": "1. Standard PII Masking",
        "text": "Иванов Иван, тел +79001234567. Почта test@test.ru.",
        "expect_device": None,
        "expect_name": "Иванов Иван",
        "expect_manual": True,
        "check_masked": "<NAME_1>, тел <PHONE_1>. Почта <EMAIL_1>.",
    },
    {
        "name": "2. Serial Number Extraction",
        "text": "Зав. номер 230201384 сломался.",
        "expect_device": "ДГС ЭРИС-230",
        "expect_name": None,
        "expect_manual": False,
        "check_masked": "Зав. номер 230201384 сломался.",
    },
    {
        "name": "3. LLM Extraction (Advant)",
        "text": "Стационарный газоанализатор Advant сломался.",
        "expect_device": "Advant",
        "expect_name": None,
        "expect_manual": False,
        "check_masked": "Стационарный газоанализатор Advant сломался.",
    },
    {
        "name": "4. Mixed Case (Name + Serial)",
        "text": "Васильева Елена, прибор 414555666.",
        "expect_device": "ПГ ЭРИС-414",
        "expect_name": "Васильева Елена",
        "expect_manual": False,
        "check_masked": "<NAME_1>, прибор 414555666.",
    },
]


async def run_tests():
    print("=== FULL LOGIC TEST SUITE ===")

    # Патчим настройки
    with patch("app.config.get_settings", return_value=mock_settings):
        # Импортируем модули ПРИМЕНЯЯ патч настроек
        import app.services.ai_processor
        from app.services.parsing.ner_extractor import extract_entities
        from app.services.parsing.serial_parser import extract_device_from_serial
        from app.services.parsing.utils import mask_pii

        # ---
        # ГЛАВНОЕ ИСПРАВЛЕНИЕ: Патчим модули-источники, а не ai_processor
        # ---
        with (
            # Патчим функцию в файле, где она определена
            patch(
                "app.services.fetcher.find_and_download_pdf", return_value=fake_pdf_path
            ) as mock_fetcher,
            # Патчим метод синглтона rag_engine
            patch(
                "app.services.rag_engine.rag_engine.get_context",
                return_value=fake_context,
            ) as mock_rag_get_context,
            # Патчим HTTP клиент
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            passed = 0
            failed = 0

            for case in test_cases:
                print(f"\n\n--- RUNNING: {case['name']} ---")
                print(f"Input: {case['text'][:60]}...")

                try:
                    # 1. NLP
                    entities = extract_entities(case["text"])

                    # Serial Logic
                    has_device = any(e["type"] == "DEVICE" for e in entities)
                    if not has_device:
                        serial_info = extract_device_from_serial(case["text"])
                        if serial_info:
                            entities.append(serial_info)

                    print(f"  Entities: {entities}")

                    # 2. Masking
                    masked_text, entity_map = mask_pii(case["text"], entities)
                    print(f"  Masked: {masked_text.replace(chr(10), ' ')}")

                    if "check_masked" in case:
                        assert case["check_masked"] == masked_text, (
                            f"Text mismatch!\nExpected: {case['check_masked']}\nActual:   {masked_text}"
                        )

                    # 3. AI Call
                    device_entity = next(
                        (e for e in entities if e["type"] == "DEVICE"), None
                    )
                    device_name = device_entity["normal"] if device_entity else None

                    # Настройка моков LLM
                    mock_client.post.return_value = get_llm_response_mock(masked_text)

                    # Спец-логика для теста LLM Extraction (Advant)
                    # Мы подменяем extract_device_with_llm внутри ai_processor
                    if case["name"] == "3. LLM Extraction (Advant)":
                        with patch(
                            "app.services.ai_processor.extract_device_with_llm",
                            return_value="Advant",
                        ):
                            result = await app.services.ai_processor.generate_response(
                                masked_text, device_name
                            )
                    else:
                        result = await app.services.ai_processor.generate_response(
                            masked_text, device_name
                        )

                    # 4. Assertions
                    assert result["manual_required"] == case["expect_manual"], (
                        f"Manual Required mismatch! Expected {case['expect_manual']}, got {result['manual_required']}"
                    )

                    # Проверяем Fetcher только если прибор был найден
                    if case["expect_device"] and not case["expect_manual"]:
                        mock_fetcher.assert_awaited_with(case["expect_device"])

                    print(f"[SUCCESS] {case['name']} passed.")
                    passed += 1

                except AssertionError as e:
                    print(f"[FAIL] {case['name']}: {e}")
                    failed += 1
                except Exception as e:
                    print(f"[ERROR] {case['name']}: {e}")
                    import traceback

                    traceback.print_exc()
                    failed += 1

            print(f"\n\n=== RESULTS: {passed} passed, {failed} failed ===")


if __name__ == "__main__":
    try:
        asyncio.run(run_tests())
    except Exception as e:
        print(f"Critical Suite Error: {e}")
        import traceback

        traceback.print_exc()
