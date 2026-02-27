import os
from functools import lru_cache

from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- General ---
    PROJECT_NAME: str = "Gas Support AI"

    # --- AI Configuration ---
    USE_MOCK_AI: bool = True  # True для экономии денег на разработке
    HF_API_TOKEN: str = ""
    HF_API_URL: str = ""

    # --- Database ---
    POSTGRES_DSN: PostgresDsn = Field(
        default="postgresql://postgres:12345678@localhost:5432/AI_SUPPORT"
    )

    # --- IMAP (Reading emails) ---
    IMAP_HOST: str = "imap.mail.ru"
    IMAP_PORT: int = 993
    IMAP_USER: str = ""
    IMAP_PASSWORD: str = ""
    IMAP_MAILBOX: str = "INBOX"

    # --- SMTP (Sending responses) ---
    SMTP_HOST: str = "smtp.mail.ru"
    SMTP_PORT: int = 465
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""

    # --- Workers ---
    POLLING_INTERVAL: int = 60

    class Config:
        # Путь к .env файлу.
        # Файл config.py находится в backend/app/, а .env в корне проекта (enigma/).
        # Поэтому поднимаемся на два уровня вверх: .. (в backend) -> .. (в enigma)
        env_file = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
