import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio, json, logging, sys
from aio_pika import connect_robust
from voice_bot.services import VoiceBotService
from queues.db_connection import get_booking_data_async
from queues.process_queue import consume_queue, process_pars
from config import rabbitmq_url, call_queue, pars_queue

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

app = FastAPI(title="VoiceBot API")
service = VoiceBotService()


# async def fetch_booking_info_from_queue(queue_name: str):
#     """
#     Connects to RabbitMQ, pulls one message off `queue_name`,
#     acknowledges it, then fetches the full booking_data from the DB.
#     """
#     conn = await connect_robust(rabbitmq_url)
#     chan = await conn.channel()
#     await chan.set_qos(prefetch_count=1)
#     queue = await chan.declare_queue(queue_name, durable=True)

#     # get exactly one message
#     incoming = await queue.get()
#     data = json.loads(incoming.body)
#     await incoming.ack()

#     booking_id = data.get("booking_id")
#     if not booking_id:
#         raise ValueError("no booking_id in queue message")

#     booking_info = await get_booking_data_async(booking_id)
#     await conn.close()
#     return booking_info


async def fetch_booking_info_from_queue(queue_name: str):
    conn = await connect_robust(rabbitmq_url)
    chan = await conn.channel()
    await chan.set_qos(prefetch_count=1)
    queue = await chan.declare_queue(queue_name, durable=True)

    print("🚀 Waiting for message from RabbitMQ...")

    incoming = None

    while True:
        try:

            incoming = await queue.get(timeout=5)
            if incoming:
                print(f"✅ Message received")
                break
        except Exception as e:
            # print(f"⚠️ No message received yet ({e})")
            await asyncio.sleep(1)
        

    if not incoming:
        await conn.close()
        raise TimeoutError(f"⛔ No messages in queue")

    data = json.loads(incoming.body)
    await incoming.ack()

    booking_id = data.get("booking_id")
    if not booking_id:
        raise ValueError("❌ No booking_id in queue message.")

    booking_info = await get_booking_data_async(booking_id)
    await conn.close()
    return booking_info



@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("🟢 Client connected, now pulling booking_info from queue…")

    try:

        booking_info = await fetch_booking_info_from_queue(call_queue)
        logger.info(f"📥 Got booking_info from queue: {booking_info}")

        system_prompt = service.build_system_prompt(booking_info)

        greeting = service.generate_greeting(booking_info)
        greeting_audio = await asyncio.to_thread(service.tts.synthesize, greeting)
        await websocket.send_bytes(greeting_audio)
        history = f"<|assistant|>{greeting}\n"

        while True:
            try:
                logger.info("👂 Ожидание аудио от клиента...")
                audio_data = await websocket.receive_bytes()
                logger.info("🎧 Получено аудио от клиента")

                logger.info("🔡 Начало распознавания речи...")
                user_text = await asyncio.to_thread(service.asr.transcribe, audio_data)
                logger.info(f"💬 Распознанный текст: '{user_text}'")

                logger.info("🧠 Генерация ответа LLM...")
                bot_reply = await asyncio.to_thread(
                    service.process_conversation,
                    user_input=user_text,
                    system_prompt=system_prompt,
                )
                logger.info(f"🤖 Ответ бота: '{bot_reply}'")

                status = service.extract_status(bot_reply)
                if status:
                    farewell = "Хорошо, спасибо! До свидания!"
                    await websocket.send_bytes(
                        await asyncio.to_thread(service.tts.synthesize, farewell)
                    )
                    logger.info("🔊 Отправлено финальное аудио")

                    await websocket.send_text(json.dumps({"status": status}))
                    logger.info(f"🔔 Статус сессии: {status}")

                    try:
                        async with httpx.AsyncClient() as client:
                            response = await client.post(
                                "https://conserj.ru/api/bookings/update_status", #TODO сделать обращение внутри докера
                                json={
                                    "booking_id": str(booking_info["booking_id"]),
                                    "status": status # "booked" or "failed"
                                },
                                timeout=5,
                            )
                            response.raise_for_status()
                        logger.info("✅ Статус успешно обновлён в бекенде")
                    except Exception as e:
                        logger.error(f"❌ Ошибка обновления статуса в бекенде: {e}")

                    break

                history += f"<|user|>{user_text}<|assistant|>{bot_reply}\n"
                logger.info("🎙 Синтез речи...")
                await websocket.send_bytes(
                    await asyncio.to_thread(service.tts.synthesize, bot_reply)
                )
                logger.info("🔊 Отправлено аудио с ответом")

            except WebSocketDisconnect:
                logger.warning("🔴 Client disconnected")
                break
            except Exception as e:
                logger.error(f"❌ Error in message loop: {e}")
                break

    except Exception as e:
        logger.error(f"⛔ Critical error before loop: {e}")
    finally:
        try:
            await websocket.close()
        except RuntimeError as e:
            logger.warning(f"🔴 WebSocket already closed: {e}")
        logger.info("🛑 WebSocket connection closed")


@app.on_event("startup")
async def startup_event():

    asyncio.create_task(consume_queue(pars_queue, process_pars))
    logger.info("🚀 Background consumer for pars_queue started")


if __name__ == "__main__":
    import uvicorn
    import os
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    uvicorn.run(app, host="0.0.0.0", port=8080, log_config=None)
