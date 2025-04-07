import asyncio
import uuid
import json
from config import *
from db_connection import AsyncSessionLocal as async_session_maker
from sqlalchemy import text
import pika

def get_booking_data_raw_sync(booking_id: str):
    async def inner():
        async with async_session_maker() as session:
            result = await session.execute(
                text(
                    """
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
                    WHERE b.id = :booking_id
                    """
                ),
                {"booking_id": booking_id},
            )
            row = result.fetchone()
            return dict(row) if row else None

    return asyncio.run(inner())

def create_queue(channel):
    call_queue = "call_queue"
    pars_queue = "pars_queue"
    channel.queue_declare(queue=call_queue)
    channel.queue_declare(queue=pars_queue)
    return call_queue, pars_queue

def callback(ch, method, properties, body):
    try:
        print(f"Received: {body}")
        data = json.loads(body)
        booking_id = data.get("booking_id")

        if booking_id:
            result = get_booking_data_raw_sync(booking_id)
            if result:
                print("Данные брони:")
                for k, v in result.items():
                    print(f"{k}: {v}")
            else:
                print("Бронь не найдена")
        else:
            print("Нет booking_id в сообщении")

    except Exception as e:
        print("Ошибка обработки:", e)

    ch.basic_ack(delivery_tag=method.delivery_tag)

if __name__ == "__main__":
    channel, connection = connect_queue()
    call_queue, pars_queue = create_queue(channel)

    channel.basic_consume(queue=call_queue, on_message_callback=callback, auto_ack=False)
    channel.basic_consume(queue=pars_queue, on_message_callback=callback, auto_ack=False)
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("Завершение...")
        channel.close()
        connection.close()
