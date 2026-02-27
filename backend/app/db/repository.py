# app/db/repository.py
import asyncpg
from uuid import UUID, uuid4
from typing import Optional, List, Dict
from datetime import datetime, timezone

class MessageRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def create_message(self, data: Dict) -> UUID:
        query = """
            INSERT INTO messages (
                id, date, full_name, object, phone_num, email,
                device_num, device_type, emotional_col, message,
                llm_response, processed
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            RETURNING id
        """
        async with self.pool.acquire() as conn:
            msg_id = data.get('id') or uuid4()
            await conn.execute(
                query,
                msg_id,
                datetime.now(timezone.utc),  # явно передаём дату
                data['full_name'],
                data['object'],
                data['phone_num'],
                data['email'],
                data['device_num'],
                data['device_type'],
                data['emotional_col'],
                data['message'],
                data.get('llm_response'),
                data.get('processed', False)
            )
            return msg_id

    async def get_all_messages(self) -> List[Dict]:
        query = "SELECT * FROM messages ORDER BY date DESC"
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query)
            return [dict(row) for row in rows]

    async def get_message(self, msg_id: UUID) -> Optional[Dict]:
        query = "SELECT * FROM messages WHERE id = $1"
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, msg_id)
            return dict(row) if row else None

    async def update_message(self, msg_id: UUID, data: Dict) -> bool:
        fields = []
        values = []
        idx = 2
        for key, val in data.items():
            if key not in ('id', 'date'):  # не обновляем первичный ключ и дату создания
                fields.append(f"{key} = ${idx}")
                values.append(val)
                idx += 1
        if not fields:
            return False
        query = f"UPDATE messages SET {', '.join(fields)} WHERE id = $1"
        values.insert(0, msg_id)
        async with self.pool.acquire() as conn:
            result = await conn.execute(query, *values)
            return result == "UPDATE 1"

    async def delete_message(self, msg_id: UUID) -> bool:
        query = "DELETE FROM messages WHERE id = $1"
        async with self.pool.acquire() as conn:
            result = await conn.execute(query, msg_id)
            return result == "DELETE 1"