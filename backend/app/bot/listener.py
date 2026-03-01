import json
import logging

import redis.asyncio as redis
from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.config import settings

logger = logging.getLogger(__name__)

# Маппинг ключей от Backend в русские подписи
FIELD_MAP = {
    "created_at": "Дата",
    "full_name": "ФИО",
    "object_name": "Объект",
    "phone_num": "Телефон",
    "email": "Email",
    "device_num": "Зав. номер",
    "device_type": "Тип прибора",
    "sentiment": "Тональность",
    "summary": "Кратко",
}

SENTIMENT_EMOJI = {"positive": "🟢", "neutral": "⚪", "negative": "🔴"}


async def listen_redis(bot: Bot):
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = redis_client.pubsub()

    try:
        await pubsub.subscribe(settings.REDIS_CHANNEL)
        logger.info(f"Bot started listening Redis channel: {settings.REDIS_CHANNEL}")

        rr_key = "round_robin_index"

        async for message in pubsub.listen():
            if message["type"] != "message":
                continue

            try:
                data = json.loads(message["data"])
                logger.info(f"Received ticket data: {data}")

                msg_lines = ["🆕 <b>Новое обращение</b>\n"]

                for eng_key, rus_label in FIELD_MAP.items():
                    # Получаем значение, если его нет или оно None -> ставим дефолт
                    value = data.get(eng_key)

                    if not value:
                        value = "не указано"

                    # Добавляем эмодзи для сентимента
                    if eng_key == "sentiment":
                        # Приводим к нижнему регистру только если value не дефолт
                        emoji = SENTIMENT_EMOJI.get(value.lower(), "❓")
                        value = f"{emoji} {value}"

                    msg_lines.append(f"<b>{rus_label}:</b> {value}")

                text = "\n".join(msg_lines)

                keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="Открыть тикет", url=settings.FRONTEND_URL
                            )
                        ]
                    ]
                )

                if not settings.TELEGRAM_TOPIC_IDS:
                    logger.warning("No Telegram Topic IDs configured!")
                    continue

                current_index_str = await redis_client.get(rr_key)
                current_index = int(current_index_str) if current_index_str else 0

                topic_ids = settings.TELEGRAM_TOPIC_IDS
                target_topic_id = topic_ids[current_index % len(topic_ids)]

                next_index = (current_index + 1) % len(topic_ids)
                await redis_client.set(rr_key, next_index)

                await bot.send_message(
                    chat_id=settings.TELEGRAM_GROUP_ID,
                    message_thread_id=target_topic_id,
                    text=text,
                    parse_mode="HTML",
                    reply_markup=keyboard,
                )
                logger.info(f"Notification sent to topic {target_topic_id}")

            except json.JSONDecodeError:
                logger.error(f"Failed to decode JSON: {message['data']}")
            except Exception as e:
                logger.error(f"Error processing ticket: {e}", exc_info=True)

    except Exception as e:
        logger.critical(f"Redis listener crashed: {e}")
    finally:
        await pubsub.unsubscribe(settings.REDIS_CHANNEL)
        await redis_client.close()
