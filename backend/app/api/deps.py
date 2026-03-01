from app.db.repository import MessageRepository
from fastapi import Request

def get_repository(request: Request) -> MessageRepository:
    pool = request.app.state.db_pool
    return MessageRepository(pool)