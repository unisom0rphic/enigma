# app/services/email_service.py
from uuid import UUID
import imaplib
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import parsedate_to_datetime
from typing import List, Dict
import asyncio
from app.config import settings
from app.db.repository import MessageRepository
from app.services.parsing import extract_entities, analyze_sentiment, summarize
from app.services.ai_processor import call_external_ai
import logging
import email.header

import re

logger = logging.getLogger(__name__)







class EmailService:
    def __init__(self, repo: MessageRepository):
        self.repo = repo
        
        # IMAP Config...
        self.imap_host = settings.IMAP_HOST
        self.imap_port = settings.IMAP_PORT
        self.username = settings.IMAP_USER
        self.password = settings.IMAP_PASSWORD
        self.mailbox = settings.IMAP_MAILBOX
        
        # SMTP Config (для отправки ответов)
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD

    # ... (существующие методы fetch_new_emails, _fetch_emails_sync, _get_email_body, process_and_save_emails остаются без изменений) ...
    
    async def fetch_new_emails(self) -> List[Dict]:
        """Подключается к IMAP, получает новые письма и возвращает список словарей с данными."""
        loop = asyncio.get_event_loop()
        emails = await loop.run_in_executor(None, self._fetch_emails_sync)
        return emails

    def _fetch_emails_sync(self):
        # ... (код метода без изменений) ...
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Connecting to IMAP server {self.imap_host}...")
        with imaplib.IMAP4_SSL(self.imap_host, self.imap_port) as imap:
            imap.login(self.username, self.password)
            imap.select(self.mailbox)
            logger.info("IMAP login successful, searching for UNSEEN messages...")
            
            status, messages = imap.search(None, 'UNSEEN')
            msg_ids = messages[0].split()
            logger.info(f"Found {len(msg_ids)} unseen messages")
            
            results = []
            for msg_id in msg_ids:
                logger.info(f"Processing message ID: {msg_id}")
                status, data = imap.fetch(msg_id, '(RFC822)')
                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)

                body = self._get_email_body(msg)

                from_header = msg.get('From', '')
                if from_header:
                    from_str = str(email.header.make_header(email.header.decode_header(from_header)))
                    email_match = re.search(r'<(.+?)>', from_str)
                    email_addr = email_match.group(1) if email_match else from_str
                else:
                    email_addr = ''

                date = parsedate_to_datetime(msg.get('Date'))

                extracted = extract_entities(body) 
                sentiment = analyze_sentiment(body)
                summary = summarize(body)

                ticket_data = {
                    'full_name': extracted.get('full_name', ''),
                    'object': extracted.get('object', ''),
                    'phone_num': extracted.get('phone_num', ''),
                    'email': email_addr,
                    'device_num': extracted.get('device_num', ''),
                    'device_type': extracted.get('device_type', ''),
                    'emotional_col': sentiment,
                    'message': body,
                    'llm_response': '',
                    'processed': False,
                }
                results.append(ticket_data)
                imap.store(msg_id, '+FLAGS', '\\Seen')

            return results

    def _get_email_body(self, msg):
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    return part.get_payload(decode=True).decode(errors='ignore')
        else:
            return msg.get_payload(decode=True).decode(errors='ignore')
        return ""

    async def process_and_save_emails(self):
        emails = await self.fetch_new_emails()
        logger.info(f"Fetched {len(emails)} emails to save")
        for email_data in emails:
            msg_id = await self.repo.create_message(email_data)
            logger.info(f"Saved new ticket {msg_id}")
            asyncio.create_task(self._generate_ai_response(msg_id, email_data['message']))

    async def _generate_ai_response(self, ticket_id: UUID, message_text: str):
        response = await call_external_ai(message_text)
        await self.repo.update_message(ticket_id, {'llm_response': response})

    # --- НОВЫЙ ФУНКЦИОНАЛ ---

    async def send_reply(self, to_email: str, response_text: str):
        """
        Асинхронно отправляет ответ пользователю через SMTP.
        Использует run_in_executor для блокирующего вызова smtplib.
        """
        if not to_email:
            raise ValueError("Recipient email is missing")
        
        loop = asyncio.get_event_loop()
        # Запускаем синхронную отправку в отдельном потоке, чтобы не блокировать event loop
        await loop.run_in_executor(None, self._send_email_sync, to_email, response_text)

    def _send_email_sync(self, to_email: str, response_text: str):
        """Синхронная логика отправки письма. Поддерживает SSL (465) и STARTTLS (587)."""
        logger.info(f"Attempting to send email to {to_email} via {self.smtp_host}:{self.smtp_port}")
        
        msg = EmailMessage()
        msg['Subject'] = "Re: Ваше обращение в службу поддержки"
        msg['From'] = self.smtp_user
        msg['To'] = to_email
        msg.set_content(response_text)

        context = ssl.create_default_context()

        try:
            # Если порт 465 — используем SMTP_SSL
            if self.smtp_port == 465:
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=context, timeout=15) as server:
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(msg)
            
            # Если порт 587 (или другой) — используаем SMTP + STARTTLS
            else:
                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=15) as server:
                    server.ehlo()  # Начало сессии
                    server.starttls(context=context)  # Включение шифрования
                    server.ehlo()
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(msg)

            logger.info(f"Email successfully sent to {to_email}")

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP Authentication failed. Check login/password. Details: {e}")
            raise Exception("SMTP Authentication Error: Check login/password or app-specific password.")
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            raise