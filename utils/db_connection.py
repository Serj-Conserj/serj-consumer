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
            b.id AS booking_id,
            b.booking_date,
            b.num_of_people AS people,
            b.special_requests,
            u.first_name AS name,
            u.phone AS phone,
            p.address AS address,
            p.full_name AS place_name,
            bl.type As type,
            bl.url AS url
        FROM bookings b
        JOIN members u ON b.user_id = u.id
        JOIN places p ON b.place_id = p.id
        LEFT JOIN booking_links bl ON bl.place_id = p.id
        WHERE b.id = $1
        ORDER BY bl.type DESC  -- This will prioritize 'main' type if it exists
        LIMIT 1
        """,
        booking_id,
    )
    await conn.close()

    if not row:
        return None

    return {
        "booking_id": row["booking_id"],
        "date": row["booking_date"],
        "people": row["people"],
        "special_requests": row["special_requests"],
        "place_name": row["place_name"],
        "phone": row["phone"][1:],
        "name": row["name"],
        "address": row["address"],
        "url": row.get("url", None),
    }
