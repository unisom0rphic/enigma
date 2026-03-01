# app/api/v1/schemas.py
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr


class TicketBase(BaseModel):
    full_name: Optional[str] = None
    phone_num: Optional[str] = None
    email: Optional[EmailStr] = None
    object_name: Optional[str] = None
    device_type: Optional[str] = None
    device_num: Optional[str] = None


class TicketCreate(TicketBase):
    original_message: str
    # Поля ниже опциональны, так как их заполнит AI
    sentiment: Optional[str] = None
    category: Optional[str] = None
    summary: Optional[str] = None
    llm_response: Optional[str] = None
    is_important: bool = False
    manual_required: bool = False
    is_relevant: bool = True


class TicketUpdate(BaseModel):
    full_name: Optional[str] = None
    phone_num: Optional[str] = None
    email: Optional[EmailStr] = None
    object_name: Optional[str] = None
    device_type: Optional[str] = None
    device_num: Optional[str] = None
    llm_response: Optional[str] = None
    is_resolved: Optional[bool] = None
    manual_required: Optional[bool] = None


class TicketResponse(TicketBase):
    id: UUID
    created_at: datetime

    original_message: str
    summary: Optional[str]
    llm_response: Optional[str]

    sentiment: Optional[str]
    category: Optional[str]

    is_resolved: bool
    is_important: bool
    manual_required: bool
    is_relevant: bool

    class Config:
        from_attributes = True
