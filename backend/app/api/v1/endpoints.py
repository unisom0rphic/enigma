# app/api/v1/endpoints.py
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_repository
from app.api.v1 import schemas
from app.db.repository import MessageRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.get("/", response_model=list[schemas.TicketResponse])
async def get_all_tickets(repo: MessageRepository = Depends(get_repository)):
    # По умолчанию не показываем resolved (логика внутри repo)
    messages = await repo.get_tickets(show_resolved=False)
    return messages


@router.post("/", response_model=UUID)
async def create_ticket(
    ticket: schemas.TicketCreate, repo: MessageRepository = Depends(get_repository)
):
    data = ticket.model_dump(exclude_unset=True)
    msg_id = await repo.create_ticket(data)
    return msg_id


@router.put("/{ticket_id}", response_model=bool)
async def update_ticket(
    ticket_id: UUID,
    updates: schemas.TicketUpdate,
    repo: MessageRepository = Depends(get_repository),
):
    # Убираем None значения
    data = {k: v for k, v in updates.model_dump().items() if v is not None}
    if not data:
        raise HTTPException(400, "No fields to update")
    success = await repo.update_ticket(ticket_id, data)
    if not success:
        raise HTTPException(404, "Ticket not found")
    return success


@router.delete("/{ticket_id}", response_model=bool)
async def delete_ticket(
    ticket_id: UUID, repo: MessageRepository = Depends(get_repository)
):
    success = await repo.delete_ticket(ticket_id)
    if not success:
        raise HTTPException(404, "Ticket not found")
    return success


@router.post("/{ticket_id}/approve", response_model=dict)
async def approve_and_send_ticket(
    ticket_id: UUID, repo: MessageRepository = Depends(get_repository)
):
    """
    Подтверждает ответ AI, отправляет письмо пользователю и закрывает тикет.
    """
    # 1. Получаем тикет
    ticket = await repo.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # 2. Проверки
    if ticket.get("is_resolved"):
        raise HTTPException(status_code=400, detail="Ticket is already resolved")

    llm_response = ticket.get("llm_response")
    if not llm_response:
        raise HTTPException(status_code=400, detail="Cannot send empty response")

    recipient_email = ticket.get("email")
    if not recipient_email:
        raise HTTPException(status_code=400, detail="Ticket has no email address")

    # 3. Отправляем письмо
    # Инициализируем сервис (в реальном проекте лучше через Depends, но тут ок)
    from app.services.email_service import EmailService

    email_service = EmailService(repo)

    try:
        # Используем метод send_reply
        await email_service.send_reply(recipient_email, llm_response)
    except Exception as e:
        logger.error(f"SMTP sending failed: {e}")
        raise HTTPException(status_code=503, detail=f"Failed to send email: {str(e)}")

    # 4. Обновляем статус в БД (ставим is_resolved = True)
    await repo.update_ticket(ticket_id, {"is_resolved": True})

    return {"status": "success", "message": "Reply sent and ticket closed"}


from pydantic import BaseModel

from app.services.parsing.ner_extractor import extract_entities
from app.services.parsing.utils import mask_pii


# Схема для входящего текста
class DebugText(BaseModel):
    text: str


@router.post("/debug/nlp")
async def debug_nlp(request: DebugText):
    """
    Тест NLP без базы и почты.
    Принимает текст, возвращает найденные сущности и маскированный текст.
    """
    # 1. Извлечение сущностей
    entities = extract_entities(request.text)

    # 2. Маскирование
    masked_text, entity_map = mask_pii(request.text, entities)

    return {"entities": entities, "masked_text": masked_text, "entity_map": entity_map}
