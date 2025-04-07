import psycopg2
import os
from config import *

def get_booking_data_sync(booking_id: str):
    conn = psycopg2.connect(
        dbname=postgres_db,
        user=postgres_user,
        password=postgres_password,
        host=postgres_host,
        port=postgres_port,
    )
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            b.id AS booking_id,
            b.booking_date,
            b.recording_date,
            b.num_of_people,
            b.special_requests,
            b.confirmed,
            u.first_name,
            u.username,
            u.telegram_id,
            p.name AS place_name
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        JOIN places p ON b.place_id = p.id
        WHERE b.id = %s
    """, (booking_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if row:
        return {
            "booking_id": row[0],
            "booking_date": row[1],
            "recording_date": row[2],
            "num_of_people": row[3],
            "special_requests": row[4],
            "confirmed": row[5],
            "first_name": row[6],
            "username": row[7],
            "telegram_id": row[8],
            "place_name": row[9],
        }
    return None
