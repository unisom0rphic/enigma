# backend/tests/test_e2e.py
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.services.email_service import EmailService


@pytest.mark.asyncio
async def test_email_processing_pipeline():
    # Используем полное ФИО для корректной работы Natasha
    raw_email_body = "Здравствуйте! Меня зовут Иванов Иван. Срочно! Утечка газа. Прибор ДГС ЭРИС-230."

    mock_repo = MagicMock()
    mock_repo.create_ticket = MagicMock(return_value="test-uuid")

    # ИСПРАВЛЕНИЕ: new_callable=AsyncMock
    with patch(
        "app.services.email_service.process_ticket_ai", new_callable=AsyncMock
    ) as mock_ai:
        mock_ai.return_value = {
            "sentiment": "negative",
            "category": "неисправность",
            "important": True,
            "summary": "Утечка газа.",
            "answer": "Решаем проблему.",
            "manual_required": False,
        }

        service = EmailService(repo=mock_repo)
        email_input = {"body": raw_email_body, "email_addr": "test@test.com"}

        result = await service._process_single_email(email_input)

        assert result["full_name"] == "Иванов Иван"
        assert result["device_type"] == "ДГС ЭРИС-230"

        # Теперь проверка должна пройти
        assert result["is_important"] is True

        # Проверяем, что мок вызывался
        mock_ai.assert_called_once()
