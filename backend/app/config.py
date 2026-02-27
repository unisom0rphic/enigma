import os
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Gas Support AI"

    # AI Flags
    USE_MOCK_AI: bool = True
    HF_API_TOKEN: str = ""
    HF_API_URL: str = ""

    # DB
    DATABASE_URL: str = "postgresql://user:pass@localhost/db"

    class Config:
        # Файл лежит в корне (enigma/.env), а запускаем мы из папки backend (или docker)
        # Поэтому ищем на уровень выше
        env_file = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
