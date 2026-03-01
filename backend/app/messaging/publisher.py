import json
import logging

import redis.asyncio as redis

from app.config import settings

logger = logging.getLogger(__name__)


async def publish_new_ticket(ticket_id, ticket_data):
    try:
        r = redis.from_url(settings.REDIS_URL)
        message = json.dumps(
            {
                "id": str(ticket_id),
                "created_at": str(ticket_data.get("created_at", "")),
                "full_name": ticket_data.get("full_name"),
                "phone_num": ticket_data.get("phone_num"),
                "email": ticket_data.get("email"),
                "device_type": ticket_data.get("device_type"),
                "device_num": ticket_data.get("device_num"),
                "sentiment": ticket_data.get("sentiment"),
                "summary": ticket_data.get("summary"),
            }
        )
        await r.publish(settings.REDIS_CHANNEL, message)
        await r.close()
    except Exception as e:
        logger.error(f"Failed to publish to Redis: {e}")
