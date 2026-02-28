# app/config.py
from pydantic_settings import BaseSettings
from pydantic import PostgresDsn, EmailStr, Field

class Settings(BaseSettings):
    # Database
    POSTGRES_DSN: PostgresDsn = Field(
        default="postgresql://postgres:12345678@localhost:5432/AI_SUPPORT"
    )
    
    # IMAP
    IMAP_HOST: str = "imap.mail.ru"
    IMAP_PORT: int = 993
    IMAP_USER: str
    IMAP_PASSWORD: str
    IMAP_MAILBOX: str = "INBOX"
    
    # SMTP (для отправки ответов)
    SMTP_HOST: str = "smtp.mail.ru"
    SMTP_PORT: int = 465
    SMTP_USER: str
    SMTP_PASSWORD: str
    
    # Polling interval (секунды)
    POLLING_INTERVAL: int = 60
    
    class Config:
        env_file = ".env"

settings = Settings()