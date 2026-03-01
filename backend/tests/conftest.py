# backend/tests/conftest.py
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from app.api.deps import get_repository
from app.db.repository import MessageRepository
from app.main import app
from httpx import ASGITransport, AsyncClient  # Важно: импортируем ASGITransport

# --- Глобальные настройки ---


@pytest.fixture(scope="session", autouse=True)
def set_test_env():
    # Принудительно включаем мок режим
    with patch("app.config.settings.USE_MOCK_AI", True):
        yield


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# --- Моки БД ---


@pytest.fixture(autouse=True)
def mock_db_init():
    with (
        patch("app.main.create_db_pool") as mock_pool,
        patch("app.main.init_db") as mock_init,
    ):
        mock_pool.return_value = MagicMock()
        yield


@pytest.fixture
def mock_repo():
    repo = MagicMock(spec=MessageRepository)
    repo.create_ticket = AsyncMock(return_value="test-uuid-1234")
    repo.get_tickets = AsyncMock(return_value=[])
    repo.get_ticket = AsyncMock(return_value=None)
    repo.update_ticket = AsyncMock(return_value=True)
    return repo


@pytest_asyncio.fixture
async def client(mock_repo):
    """Асинхронный клиент с правильным транспортом для httpx."""
    app.dependency_overrides[get_repository] = lambda: mock_repo

    # ИСПРАВЛЕНИЕ: Используем ASGITransport
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# --- Моки AI ---


@pytest.fixture
def mock_ai_processor():
    """Мок для AI процессора. Важно использовать new_callable=AsyncMock."""
    with patch(
        "app.services.email_service.process_ticket_ai", new_callable=AsyncMock
    ) as mock_ai:
        mock_ai.return_value = {
            "sentiment": "neutral",
            "category": "тест",
            "important": False,
            "summary": "Test summary",
            "answer": "Test answer",
            "manual_required": False,
        }
        yield mock_ai
