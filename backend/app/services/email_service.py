# app/services/email_service.py
import asyncio
import email
import email.header
import imaplib
import logging
import re
import smtplib
import ssl
from email.message import EmailMessage
from typing import Dict, List, Optional

from app.config import settings
from app.db.repository import MessageRepository
from app.services.ai_processor import process_ticket_ai
from app.services.parsing.ner_extractor import extract_entities
from app.services.parsing.utils import mask_pii, unmask_pii

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self, repo: MessageRepository):
        self.repo = repo

        # IMAP Config
        self.imap_host = settings.IMAP_HOST
        self.imap_port = settings.IMAP_PORT
        self.username = settings.IMAP_USER
        self.password = settings.IMAP_PASSWORD
        self.mailbox = settings.IMAP_MAILBOX

        # SMTP Config (Добавлено)
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD

    # --- IMAP FETCHING ---

    async def fetch_new_emails(self) -> List[Dict]:
        """Асинхронная обертка для синхронного IMAP."""
        loop = asyncio.get_event_loop()
        emails = await loop.run_in_executor(None, self._fetch_emails_sync)
        return emails or []

    def _fetch_emails_sync(self) -> List[Dict]:
        """Синхронная логика работы с IMAP сервером."""
        if not self.username or not self.password:
            logger.warning("IMAP credentials missing. Skipping fetch.")
            return []

        try:
            with imaplib.IMAP4_SSL(self.imap_host, self.imap_port) as imap:
                imap.login(self.username, self.password)
                imap.select(self.mailbox)

                status, messages = imap.search(None, "UNSEEN")
                if status != "OK":
                    return []

                msg_ids = messages[0].split()
                results = []

                for msg_id in msg_ids:
                    status, data = imap.fetch(msg_id, "(RFC822)")
                    if status != "OK":
                        continue

                    raw_email = data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    body = self._get_email_body(msg)

                    if not body:
                        continue

                    # Извлечение email отправителя
                    from_header = msg.get("From", "")
                    email_addr = ""
                    if from_header:
                        from_str = str(
                            email.header.make_header(
                                email.header.decode_header(from_header)
                            )
                        )
                        email_match = re.search(r"<(.+?)>", from_str)
                        email_addr = email_match.group(1) if email_match else from_str

                    results.append({"body": body, "email_addr": email_addr})
                    # Помечаем как прочитанное
                    imap.store(msg_id, "+FLAGS", "\\Seen")

                return results

        except Exception as e:
            logger.error(f"IMAP Connection Error: {e}")
            return []

    def _get_email_body(self, msg) -> str:
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        return part.get_payload(decode=True).decode(errors="ignore")
                    except Exception:
                        continue
        else:
            try:
                return msg.get_payload(decode=True).decode(errors="ignore")
            except Exception:
                return ""
        return ""

    # --- MAIN PROCESSING ---

    async def process_and_save_emails(self):
        """Основной цикл. Работает в главном потоке (async)."""
        emails = await self.fetch_new_emails()

        if not emails:
            return

        loop = asyncio.get_event_loop()
        from app.messaging.publisher import publish_new_ticket

        for email_data in emails:
            try:
                body = email_data["body"]
                sender = email_data["email_addr"]

                # 1. NLP (ТЯЖЕЛАЯ ЗАДАЧА) - выносим в поток, но ЖДЕМ результат
                entities = await loop.run_in_executor(None, extract_entities, body)

                # 2. Обработка (в главном потоке, безопасно для DB)
                ticket = await self._process_single_email(body, sender, entities)

                if ticket:
                    # 3. Сохранение
                    msg_id = await self.repo.create_ticket(ticket)
                    logger.info(
                        f"Ticket {msg_id} saved. Category: {ticket.get('category')}"
                    )

                    # 4. Публикация
                    await publish_new_ticket(msg_id, ticket)

            except Exception as e:
                logger.exception(f"Failed to process email: {e}")

    async def _process_single_email(
        self, body: str, sender: str, entities: List[Dict]
    ) -> Optional[Dict]:
        """Пайплайн: Mask -> AI -> Unmask."""

        mapped_data = self._map_entities_to_schema(entities, sender)

        if not self._is_relevant(entities, body):
            return {
                **mapped_data,
                "original_message": body,
                "is_relevant": False,
                "category": "спам",
                "summary": "Автоматическая фильтрация: не извлечены данные",
                "is_important": False,
                "manual_required": False,
            }

        masked_text, entity_map = mask_pii(body, entities)
        ai_result = await process_ticket_ai(masked_text, mapped_data.get("device_type"))

        clean_summary = unmask_pii(ai_result.get("summary", ""), entity_map)
        clean_answer = (
            unmask_pii(ai_result.get("answer", ""), entity_map)
            if ai_result.get("answer")
            else None
        )

        return {
            **mapped_data,
            "original_message": body,
            "summary": clean_summary,
            "llm_response": clean_answer,
            "sentiment": ai_result.get("sentiment"),
            "category": ai_result.get("category"),
            "is_important": ai_result.get("important", False),
            "manual_required": ai_result.get("manual_required", False),
            "is_relevant": True,
        }

    def _map_entities_to_schema(self, entities: List[Dict], sender_email: str) -> Dict:
        data = {
            "full_name": None,
            "phone_num": None,
            "email": sender_email,  # Берем только из заголовков письма
            "object_name": None,
            "device_type": None,
            "device_num": None,
        }

        for ent in entities:
            etype = ent["type"]
            if etype == "NAME" and not data["full_name"]:
                data["full_name"] = ent["normal"]
            elif etype == "PHONE" and not data["phone_num"]:
                data["phone_num"] = ent["normal"]
            # Убрал блок elif etype == "EMAIL" ...
            # так как email уже определен из sender_email
            elif etype == "DEVICE":
                if ent["text"] != ent["normal"]:
                    data["device_num"] = ent["text"]
                    data["device_type"] = ent["normal"]
                else:
                    data["device_type"] = ent["normal"]
        return data

    def _is_relevant(self, entities: List[Dict], text: str) -> bool:
        has_key_info = any(e["type"] in ["NAME", "DEVICE", "PHONE"] for e in entities)
        if not has_key_info and len(text) < 50:
            return False
        return True

    # --- SMTP SENDING ---

    async def send_reply(self, to_email: str, response_text: str):
        """Асинхронная отправка письма."""
        if not to_email:
            raise ValueError("No email")

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._send_email_sync, to_email, response_text)

    def _send_email_sync(self, to_email: str, response_text: str):
        """Синхронная отправка через SMTP."""
        if not self.smtp_user or not self.smtp_password:
            logger.warning("SMTP credentials missing")
            raise Exception("SMTP credentials not configured")

        msg = EmailMessage()
        msg["Subject"] = "Re: Ваше обращение"
        msg["From"] = self.smtp_user
        msg["To"] = to_email
        msg.set_content(response_text)

        context = ssl.create_default_context()
        try:
            if self.smtp_port == 465:
                with smtplib.SMTP_SSL(
                    self.smtp_host, self.smtp_port, context=context, timeout=15
                ) as server:
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=15) as server:
                    server.starttls(context=context)
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(msg)
            logger.info(f"Email sent to {to_email}")
        except Exception as e:
            logger.error(f"SMTP Error: {e}")
            raise
