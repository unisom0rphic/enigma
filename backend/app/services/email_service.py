# app/services/email_service.py
import asyncio
import email
import email.header
import imaplib
import logging
import re
from email.utils import parsedate_to_datetime
from typing import Dict, List
from uuid import UUID

from services.ai_processor_orig import call_external_ai

from app.config import settings
from app.db.repository import MessageRepository
from app.services.parsing import analyze_sentiment, extract_entities, summarize

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self, repo: MessageRepository):
        self.repo = repo
        self.imap_host = settings.IMAP_HOST
        self.imap_port = settings.IMAP_PORT
        self.username = settings.IMAP_USER
        self.password = settings.IMAP_PASSWORD
        self.mailbox = settings.IMAP_MAILBOX

    async def fetch_new_emails(self) -> List[Dict]:
        """Подключается к IMAP, получает новые письма и возвращает список словарей с данными."""
        loop = asyncio.get_event_loop()
        # IMAP — синхронная библиотека, запускаем в отдельном потоке
        emails = await loop.run_in_executor(None, self._fetch_emails_sync)
        return emails

    def _fetch_emails_sync(self):
        with imaplib.IMAP4_SSL(self.imap_host, self.imap_port) as imap:
            imap.login(self.username, self.password)
            imap.select(self.mailbox)

            status, messages = imap.search(None, "UNSEEN")
            msg_ids = messages[0].split()
            results = []
            for msg_id in msg_ids:
                status, data = imap.fetch(msg_id, "(RFC822)")
                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)

                body = self._get_email_body(msg)

                # Обработка заголовка From
                from_header = msg.get("From", "")
                if from_header:
                    # Декодируем в строку
                    from_str = str(
                        email.header.make_header(
                            email.header.decode_header(from_header)
                        )
                    )
                    # Извлекаем email из угловых скобок, если есть
                    email_match = re.search(r"<(.+?)>", from_str)
                    email_addr = email_match.group(1) if email_match else from_str
                else:
                    email_addr = ""

                date = parsedate_to_datetime(msg.get("Date"))

                # Заглушки NLP (заменить на реальные вызовы)
                extracted = extract_entities(body)  # возвращает dict
                sentiment = analyze_sentiment(body)  # строка
                summary = summarize(body)  # строка

                ticket_data = {
                    "full_name": extracted.get("full_name", ""),
                    "object": extracted.get("object", ""),
                    "phone_num": extracted.get("phone_num", ""),
                    "email": email_addr,
                    "device_num": extracted.get("device_num", ""),
                    "device_type": extracted.get("device_type", ""),
                    "emotional_col": sentiment,
                    "message": body,
                    "llm_response": "",
                    "processed": False,
                }
                results.append(ticket_data)
                # Помечаем письмо как прочитанное
                imap.store(msg_id, "+FLAGS", "\\Seen")

            return results

    def _get_email_body(self, msg):
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    return part.get_payload(decode=True).decode(errors="ignore")
        else:
            return msg.get_payload(decode=True).decode(errors="ignore")
        return ""

    async def process_and_save_emails(self):
        """Основной метод, вызываемый воркером."""
        emails = await self.fetch_new_emails()
        for email_data in emails:
            # Сохраняем в БД
            msg_id = await self.repo.create_message(email_data)
            # После сохранения можно асинхронно запустить обращение к AI для генерации ответа
            asyncio.create_task(
                self._generate_ai_response(msg_id, email_data["message"])
            )
            logger.info(f"Saved new ticket {msg_id}")

    async def _generate_ai_response(self, ticket_id: UUID, message_text: str):
        """Запрос к внешнему AI (RAG) для формулировки ответа."""
        # Здесь будет вызов ai_processor.call_external_ai с RAG
        response = await call_external_ai(message_text)  # заглушка
        # Обновляем запись в БД
        await self.repo.update_message(ticket_id, {"llm_response": response})
