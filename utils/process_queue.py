import asyncio
import json
from aio_pika import connect_robust, IncomingMessage, Message, DeliveryMode
from config import rabbitmq_url, call_queue, pars_queue, booking_success_state
from utils.db_connection import get_booking_data_async
from utils.request import send_status_to_backend
from parsing.booking import book_table
import time


async def process_call(msg: IncomingMessage):
    async with msg.process():
        data = json.loads(msg.body)
        booking_id = data.get("booking_id")
        print("[CALL] received", booking_id)
        if booking_id:
            result = await get_booking_data_async(booking_id)
            print("[CALL] result", result)
            # … отправка в call-часть …
            await asyncio.sleep(1)


async def process_pars(msg: IncomingMessage):
    async with msg.process():
        data = json.loads(msg.body)
        booking_id = data.get("booking_id")
        if booking_id:
            user_data = await get_booking_data_async(booking_id)
            try:
                resp = book_table(user_data)
                if resp.get("status") == booking_success_state:
                    await send_status_to_backend(booking_id, booking_success_state)
                    print("[PARS] ✓ Бронирование успешно отправлено")
            except Exception as e:
                print("[PARS] ⛔  Ошибка бронирования:", e)
                fallback_body = json.dumps({"booking_id": booking_id}).encode()
                conn = await connect_robust(rabbitmq_url)
                async with conn:
                    ch = await conn.channel()
                    await ch.default_exchange.publish(
                        Message(fallback_body, delivery_mode=DeliveryMode.PERSISTENT),
                        routing_key=call_queue,
                    )
                print(f"[PARS] {booking_id} отправлен в {call_queue} для дозвона")


async def consume_queue(queue_name: str, processor):

    conn = await connect_robust(rabbitmq_url)
    chan = await conn.channel()
    await chan.set_qos(prefetch_count=1)
    queue = await chan.declare_queue(queue_name, durable=True)
    await queue.consume(processor)
    print(f"[INFO] consuming {queue_name}")
    return conn
