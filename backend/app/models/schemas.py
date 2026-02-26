from typing import Optional
from uuid import UUID

from pydantic import BaseModel, field_validator


# Модель для входящих данных (используется при POST)
class MessageCreate(BaseModel):
    id: Optional[UUID] = (
        None  # Делаем опциональным, если хотим генерировать на сервере, или оставляем обязательным как было
    )
    full_name: str
    object: str
    phone_num: str
    email: str
    device_num: str
    device_type: str
    emotional_col: str
    message: str


# Модель для ответа (используется при GET) с переименованными полями
class MessageResponse(BaseModel):
    id: UUID
    date: str
    name: str  # full_name -> name
    object: str
    phone: str  # phone_num -> phone
    email: str
    factory_numbers: str  # device_num -> factory_numbers
    device_type: str
    sentiment: str  # emotional_col -> sentiment
    issue: str  # message -> issue

    # Новые вычисляемые поля
    email_domain: str
    phone_type: str

    # Валидатор для извлечения домена почты
    @field_validator("email_domain", mode="before")
    @classmethod
    def get_email_domain(cls, v, info):
        email = info.data.get("email", "")
        if "@" in email:
            return email.split("@")[1]
        return "unknown"

    # Валидатор для определения типа телефона (простая эвристика)
    @field_validator("phone_type", mode="before")
    @classmethod
    def get_phone_type(cls, v, info):
        phone = info.data.get("phone", "")
        # Простая логика: если начинается с +7/8 и длина 11 цифр - мобильный (для РФ)
        # В реальном проекте лучше использовать библиотеку phonenumbers
        clean_phone = "".join(filter(str.isdigit, phone))
        if len(clean_phone) == 11 and clean_phone[0] in ("7", "8"):
            return "mobile"
        return "landline"
