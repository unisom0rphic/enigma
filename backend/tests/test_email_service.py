# backend/tests/test_email_service.py
from unittest.mock import MagicMock

import pytest
from app.services.email_service import EmailService


@pytest.mark.asyncio
async def test_email_processing_pipeline(mock_ai_processor):
    """
    Тестируем полный pipeline обработки письма, но с моком БД и AI.
    """
    # 1. Подготовка данных
    # ИСПОЛЬЗУЕМ ПОЛНОЕ ИМЯ, чтобы Natasha его нашла
    email_input = {
        "body": "Здравствуйте! Я Петр Петров. Сломался прибор ДГС ЭРИС-230.",
        "email_addr": "test@mail.ru",
    }

    # 2. Мокаем репозиторий
    mock_repo = MagicMock()
    mock_repo.create_ticket = MagicMock(return_value="new-uuid")

    # 3. Запускаем обработку
    service = EmailService(repo=mock_repo)
    result = await service._process_single_email(email_input)

    # 4. Проверки
    # Имя должно извлечься
    assert result["full_name"] == "Петр Петров"

    # Прибор
    assert result["device_type"] == "ДГС ЭРИС-230"

    # Флаги из мока (mock_ai_processor из conftest)
    assert result["category"] == "тест"
