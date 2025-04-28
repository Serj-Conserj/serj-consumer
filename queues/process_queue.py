import asyncio
import json
from aio_pika import connect_robust, IncomingMessage
from config import rabbitmq_url, call_queue, pars_queue
from queues.db_connection import get_booking_data_async
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
        print("[PARS] received", booking_id)
        if booking_id:
            result = await get_booking_data_async(booking_id)
            print("[PARS] result", result)
            # … отправка в parsing-часть …
            await asyncio.sleep(100)


async def consume_queue(queue_name: str, processor):

    conn = await connect_robust(rabbitmq_url)
    chan = await conn.channel()
    await chan.set_qos(prefetch_count=1)
    queue = await chan.declare_queue(queue_name, durable=True)
    await queue.consume(processor)
    print(f"[INFO] consuming {queue_name}")
    return conn
