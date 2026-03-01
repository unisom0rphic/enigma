# backend/tests/test_api.py
import pytest


@pytest.mark.asyncio
async def test_get_tickets_empty(client, mock_repo):
    response = await client.get("/api/v1/tickets")
    assert response.status_code == 200
    assert response.json() == []
    mock_repo.get_tickets.assert_called_once()


@pytest.mark.asyncio
async def test_create_ticket(client, mock_repo):
    test_data = {"original_message": "Test message", "full_name": "Test User"}

    response = await client.post("/api/v1/tickets", json=test_data)

    assert response.status_code == 200
    assert response.json() == "test-uuid-1234"

    call_args = mock_repo.create_ticket.call_args[0][0]
    assert call_args["original_message"] == "Test message"
