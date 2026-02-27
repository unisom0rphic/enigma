# app/api/v1/schemas.py
from pydantic import BaseModel, field_validator, EmailStr
from uuid import UUID
from datetime import datetime
from typing import Optional

class MessageBase(BaseModel):
    full_name: str
    object: str
    phone_num: str
    email: EmailStr
    device_num: str
    device_type: str
    emotional_col: str
    message: str

class MessageCreate(MessageBase):
    id: Optional[UUID] = None   # если не указан, сгенерируется на сервере
    llm_response: Optional[str] = None
    processed: bool = False

class MessageUpdate(BaseModel):
    full_name: Optional[str] = None
    object: Optional[str] = None
    phone_num: Optional[str] = None
    email: Optional[EmailStr] = None
    device_num: Optional[str] = None
    device_type: Optional[str] = None
    emotional_col: Optional[str] = None
    message: Optional[str] = None
    llm_response: Optional[str] = None
    processed: Optional[bool] = None

class MessageResponse(BaseModel):
    id: UUID
    date: datetime
    full_name: str
    object: str
    phone_num: str
    email: str
    device_num: str
    device_type: str
    emotional_col: str
    message: str
    llm_response: Optional[str]
    processed: bool

    # Вычисляемые поля для фронта (опционально)
    email_domain: str = ""
    phone_type: str = ""

    @field_validator("email_domain", mode="before")
    def extract_domain(cls, v, info):
        email = info.data.get("email", "")
        return email.split("@")[1] if "@" in email else "unknown"

    @field_validator("phone_type", mode="before")
    def detect_phone_type(cls, v, info):
        phone = info.data.get("phone_num", "")
        clean = "".join(filter(str.isdigit, phone))
        if len(clean) == 11 and clean[0] in ("7", "8"):
            return "mobile"
        return "landline"