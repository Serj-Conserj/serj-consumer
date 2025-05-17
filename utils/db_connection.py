import os
import asyncpg
from config import (
    postgres_db,
    postgres_user,
    postgres_password,
    postgres_host,
    postgres_port,
)
from utils.logger import logger  # 🔹 добавляем логгер


async def get_booking_data_async(booking_id: str):
    logger.info(f"📥 Получение данных брони из бд booking_id={booking_id}")

    conn = await asyncpg.connect(
        user=postgres_user,
        password=postgres_password,
        database=postgres_db,
        host=postgres_host,
        port=postgres_port,
    )

    try:
        row = await conn.fetchrow(
            """
            SELECT
                b.id AS booking_id,
                b.booking_date,
                b.num_of_people AS people,
                b.special_requests,
                u.first_name AS name,
                u.phone AS phone,
                p.address AS address,
                p.full_name AS place_name,
                bl.type AS type,
                bl.url AS url
            FROM bookings b
            JOIN members u ON b.user_id = u.id
            JOIN places p ON b.place_id = p.id
            LEFT JOIN booking_links bl ON bl.place_id = p.id
            WHERE b.id = $1
            ORDER BY bl.type DESC
            LIMIT 1
            """,
            booking_id,
        )
    finally:
        await conn.close()

    if not row:
        logger.warning(f"⚠️ Бронь с booking_id={booking_id} не найдена в базе")
        return None

    logger.info(f"✅ Данные брони booking_id={booking_id} успешно получены из бд")

    return {
        "booking_id": row["booking_id"],
        "date": row["booking_date"],
        "people": row["people"],
        "special_requests": row["special_requests"],
        "place_name": row["place_name"],
        "phone": row["phone"][1:],  # убираем + в начале
        "name": row["name"],
        "address": row["address"],
        "url": row.get("url", None),
    }
