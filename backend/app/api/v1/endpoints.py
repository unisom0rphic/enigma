# app/api/v1/endpoints.py
from fastapi import APIRouter, HTTPException, Depends
from uuid import UUID
from app.api.v1 import schemas
from app.db.repository import MessageRepository
from app.api.deps import get_repository
from app.services.email_service import EmailService  # Импортируем сервис
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tickets", tags=["tickets"])

@router.get("/", response_model=list[schemas.MessageResponse])
async def get_all_tickets(
    repo: MessageRepository = Depends(get_repository)
):
    messages = await repo.get_all_messages()
    return messages

@router.post("/", response_model=UUID)
async def create_ticket(
    ticket: schemas.MessageCreate,
    repo: MessageRepository = Depends(get_repository)
):
    data = ticket.dict(exclude_unset=True)
    msg_id = await repo.create_message(data)
    return msg_id

@router.put("/{ticket_id}", response_model=bool)
async def update_ticket(
    ticket_id: UUID,
    updates: schemas.MessageUpdate,
    repo: MessageRepository = Depends(get_repository)
):
    data = {k: v for k, v in updates.dict().items() if v is not None}
    if not data:
        raise HTTPException(400, "No fields to update")
    success = await repo.update_message(ticket_id, data)
    if not success:
        raise HTTPException(404, "Ticket not found")
    return success

@router.delete("/{ticket_id}", response_model=bool)
async def delete_ticket(
    ticket_id: UUID,
    repo: MessageRepository = Depends(get_repository)
):
    success = await repo.delete_message(ticket_id)
    if not success:
        raise HTTPException(404, "Ticket not found")
    return success

# --- НОВЫЙ ЭНДПОИНТ ---

@router.post("/{ticket_id}/approve", response_model=dict)
async def approve_and_send_ticket(
    ticket_id: UUID,
    repo: MessageRepository = Depends(get_repository)
):
    """
    Подтверждает тикет, отправляет ответ пользователю по SMTP 
    и выставляет processed=True.
    """
    # 1. Получаем тикет
    ticket = await repo.get_message(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # 2. Проверки бизнес-логики
    if ticket.get('processed'):
        raise HTTPException(status_code=400, detail="Ticket is already processed")
    
    llm_response = ticket.get('llm_response')
    if not llm_response:
        raise HTTPException(status_code=400, detail="Cannot send empty response (llm_response is missing)")

    recipient_email = ticket.get('email')
    if not recipient_email:
        raise HTTPException(status_code=400, detail="Ticket has no email address")

    # 3. Отправляем письмо
    email_service = EmailService(repo)
    try:
        await email_service.send_reply(recipient_email, llm_response)
    except Exception as e:
        logger.error(f"SMTP sending failed: {e}")
        # Можно выбросить 500 ошибку или сообщить, что письмо не ушло
        raise HTTPException(status_code=503, detail=f"Failed to send email: {str(e)}")

    # 4. Обновляем статус в БД
    await repo.update_message(ticket_id, {'processed': True})

    return {"status": "success", "message": "Reply sent and ticket closed"}