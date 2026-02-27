# app/api/v1/endpoints.py
from fastapi import APIRouter, HTTPException, Depends
from uuid import UUID
from app.api.v1 import schemas
from app.db.repository import MessageRepository
from app.api.deps import get_repository

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
    # Убираем None значения, чтобы не обновлять поля без изменений
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