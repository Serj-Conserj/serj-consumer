import asyncio
import uuid
import json
import time
from config import *
from db_connection import get_booking_data_sync
import pika
from config import call_queue, pars_queue

def create_queue(channel):
    channel.queue_declare(queue=call_queue)
    channel.queue_declare(queue=pars_queue)
    return call_queue, pars_queue

def callback(ch, method, properties, body):
    try:

        data = json.loads(body)
        booking_id = data.get("booking_id")

        if booking_id:
            result = get_booking_data_sync(booking_id)
            if result:
                if method.routing_key == call_queue:
                    #TODO send data to a call part 
                    print(call_queue , "Result ", result)

                    pass
                if method.routing_key == pars_queue:
                    #TODO send data to a parsing part 
                    print(pars_queue , "Result ", result)
                    time.sleep(10)
                    pass
                
    except Exception as e:
        print("Ошибка обработки:", e)

    ch.basic_ack(delivery_tag=method.delivery_tag)

if __name__ == "__main__":
    channel, connection = connect_queue()
    call_queue, pars_queue = create_queue(channel)

    # Limit to one unacknowledged message at a time (ensures one task is processed before the next is received)
    channel.basic_qos(prefetch_count=1)  

    channel.basic_consume(queue=call_queue, on_message_callback=callback, auto_ack=False)
    channel.basic_consume(queue=pars_queue, on_message_callback=callback, auto_ack=False)

    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("\nЗавершение...")
        channel.close()
        connection.close()
