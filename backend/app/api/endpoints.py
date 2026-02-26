from uuid import uuid4

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from ..db import engine
from ..models.schemas import MessageCreate, MessageResponse

router = APIRouter()


@router.get("/messages", response_model=list[MessageResponse])
def get_all_messages():
    try:
        with engine.connect() as conn:
            # Запрашиваем данные, имена колонок совпадают с БД
            query = text("""
                SELECT id,
                       date::text,
                       full_name,
                       object,
                       phone_num,
                       email,
                       device_num,
                       device_type,
                       emotional_col,
                       message
                FROM messages
            """)
            result = conn.execute(query)
            rows = result.fetchall()

            response_data = []
            for row in rows:
                # Маппим сырые данные в словарь, соответствующий MessageResponse
                # Pydantic сам вызовет computed_field валидаторы
                item_dict = {
                    "id": row[0],
                    "date": row[1],
                    "name": row[2],  # full_name -> name
                    "object": row[3],
                    "phone": row[4],  # phone_num -> phone
                    "email": row[5],
                    "factory_numbers": row[6],  # device_num -> factory_numbers
                    "device_type": row[7],
                    "sentiment": row[8],  # emotional_col -> sentiment
                    "issue": row[9],  # message -> issue
                    # Эти поля будут перезаписаны валидаторами, но должны быть в dict
                    "email_domain": "",
                    "phone_type": "",
                }
                # Валидация и вычисление полей через Pydantic
                response_data.append(MessageResponse(**item_dict))

            return response_data
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при получении данных")


@router.post("/messages")
def put_message(mess: MessageCreate):
    try:
        # Если ID не передан, генерируем новый
        if not mess.id:
            mess.id = uuid4()

        with engine.connect() as conn:
            query = text("""
                INSERT INTO messages
                (id, date, full_name, object, phone_num, email, device_num, device_type, emotional_col, message)
                VALUES (:id, NOW(), :full_name, :object, :phone_num, :email, :device_num, :device_type, :emotional_col, :message)
            """)
            values = {
                "id": mess.id,
                "full_name": mess.full_name,
                "object": mess.object,
                "phone_num": mess.phone_num,
                "email": mess.email,
                "device_num": mess.device_num,
                "device_type": mess.device_type,
                "emotional_col": mess.emotional_col,
                "message": mess.message,
            }
            conn.execute(query, values)
            conn.commit()  # Явный коммит для autocommit=False или транзакций
        return {"success": True}
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при сохранении данных")
