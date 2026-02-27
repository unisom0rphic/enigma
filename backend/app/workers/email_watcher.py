# app/workers/email_watcher.py
import asyncio
import logging
from app.services.email_service import EmailService
from app.db.repository import MessageRepository
from app.config import settings

logger = logging.getLogger(__name__)

async def email_polling_worker(repo: MessageRepository):
    """Периодически опрашивает почту."""
    service = EmailService(repo)
    while True:
        try:
            await service.process_and_save_emails()
        except Exception as e:
            logger.exception("Error in email polling")
        await asyncio.sleep(settings.POLLING_INTERVAL)