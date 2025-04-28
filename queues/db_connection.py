import os
import asyncpg
from config import (
    postgres_db,
    postgres_user,
    postgres_password,
    postgres_host,
    postgres_port,
)


async def get_booking_data_async(booking_id: str):
    conn = await asyncpg.connect(
        user=postgres_user,
        password=postgres_password,
        database=postgres_db,
        host=postgres_host,
        port=postgres_port,
    )
    row = await conn.fetchrow(
        """
        SELECT
            b.id           AS booking_id,
            b.booking_date,
            b.recording_date,
            b.num_of_people,
            b.special_requests,
            b.confirmed,
            u.first_name,
            u.username,
            u.telegram_id,
            p.name         AS place_name
        FROM bookings b
        JOIN members u  ON b.user_id   = u.id
        JOIN places p   ON b.place_id  = p.id
        WHERE b.id = $1
    """,
        booking_id,
    )
    await conn.close()

    if not row:
        return None

    return {
        "booking_id": row["booking_id"],
        "date": row["booking_date"],
        "date": row["recording_date"],
        "people": row["num_of_people"],
        # "special_requests": row["special_requests"],
        # "confirmed": row["confirmed"],
        "name": row["first_name"],
        # "username": row["username"],
        # "telegram_id": row["telegram_id"],
        "address": row["place_name"],
    }
