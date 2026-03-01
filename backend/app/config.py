import os
from functools import lru_cache
from typing import List

from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- General ---
    PROJECT_NAME: str = "Gas Support AI"

    # --- Paths ---
    DATA_DIR: str = os.getenv(
        "DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "data")
    )

    # --- AI Configuration ---
    USE_MOCK_AI: bool = True
    HF_API_TOKEN: str = ""
    HF_API_URL: str = ""

    # --- Database ---
    POSTGRES_DSN: PostgresDsn = Field(
        default="postgresql://postgres:postgres@localhost:5432/ai_support"
    )

    # --- IMAP ---
    IMAP_HOST: str = "imap.mail.ru"
    IMAP_PORT: int = 993
    IMAP_USER: str = ""
    IMAP_PASSWORD: str = ""
    IMAP_MAILBOX: str = "INBOX"

    # --- SMTP ---
    SMTP_HOST: str = "smtp.mail.ru"
    SMTP_PORT: int = 465
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""

    # --- Redis ---
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_CHANNEL: str = "channel:new_ticket"

    # --- Telegram Bot ---
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_GROUP_ID: int = 0
    TELEGRAM_TOPIC_IDS: List[int] = []

    # --- Frontend ---
    FRONTEND_URL: str = "http://localhost:3000"

    # --- Workers ---
    POLLING_INTERVAL: int = 60

    class Config:
        env_file = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
<<<<<<< HEAD
=======


>>>>>>> f37fb5223398d065006790523c4f329eb2753bf6
