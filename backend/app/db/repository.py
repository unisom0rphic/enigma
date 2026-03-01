# app/db/repository.py
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID, uuid4

import asyncpg


class MessageRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def create_ticket(self, data: Dict) -> UUID:
        query = """
            INSERT INTO tickets (
                id, created_at, full_name, phone_num, email, object_name,
                device_type, device_num, original_message, summary,
                llm_response, sentiment, category,
                is_resolved, is_important, manual_required, is_relevant
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
            RETURNING id
        """
        async with self.pool.acquire() as conn:
            msg_id = data.get("id") or uuid4()
            await conn.execute(
                query,
                msg_id,
                datetime.now(timezone.utc),
                data.get("full_name"),
                data.get("phone_num"),
                data.get("email"),
                data.get("object_name"),
                data.get("device_type"),
                data.get("device_num"),
                data["original_message"],
                data.get("summary"),
                data.get("llm_response"),
                data.get("sentiment"),
                data.get("category"),
                data.get("is_resolved", False),
                data.get("is_important", False),
                data.get("manual_required", False),
                data.get("is_relevant", True),
            )
            return msg_id

    async def get_tickets(self, show_resolved: bool = False) -> List[Dict]:
        """
        Получение тикетов с сортировкой:
        1. Important (DESC)
        2. Manual Required (DESC)
        3. Date (DESC)
        """
        base_query = "SELECT * FROM tickets WHERE is_relevant = TRUE"
        if not show_resolved:
            base_query += " AND is_resolved = FALSE"

        base_query += (
            " ORDER BY is_important DESC, manual_required DESC, created_at DESC"
        )

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(base_query)
            return [dict(row) for row in rows]

    async def get_ticket(self, ticket_id: UUID) -> Optional[Dict]:
        query = "SELECT * FROM tickets WHERE id = $1"
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, ticket_id)
            return dict(row) if row else None

    async def update_ticket(self, ticket_id: UUID, data: Dict) -> bool:
        fields = []
        values = []
        idx = 2
        for key, val in data.items():
            if key not in ("id", "created_at"):
                fields.append(f"{key} = ${idx}")
                values.append(val)
                idx += 1
        if not fields:
            return False
        query = f"UPDATE tickets SET {', '.join(fields)} WHERE id = $1"
        values.insert(0, ticket_id)
        async with self.pool.acquire() as conn:
            result = await conn.execute(query, *values)
            return result == "UPDATE 1"

    async def delete_ticket(self, ticket_id: UUID) -> bool:
        query = "DELETE FROM tickets WHERE id = $1"
        async with self.pool.acquire() as conn:
            result = await conn.execute(query, ticket_id)
            return result == "DELETE 1"
