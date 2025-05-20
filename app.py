from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio, json, os
from aio_pika import connect_robust
from voice_bot.services import VoiceBotService
from utils.db_connection import get_booking_data_async
from utils.process_queue import consume_queue, process_pars
from utils.request import send_status_to_backend
from config import (
    rabbitmq_url,
    call_queue,
    pars_queue,
    booking_failure_state,
    booking_success_state,
)
from utils.logger import logger


app = FastAPI(title="VoiceBot API")
service = VoiceBotService()


async def fetch_booking_info_from_queue(queue_name: str):
    conn = await connect_robust(rabbitmq_url)
    chan = await conn.channel()
    await chan.set_qos(prefetch_count=1)
    queue = await chan.declare_queue(queue_name, durable=True)

    logger.info("🚀 Waiting for message from RabbitMQ...")

    incoming = None

    while True:
        try:
            incoming = await queue.get(timeout=5)
            if incoming:
                logger.info("✅ Message received")
                break
        except Exception:
            await asyncio.sleep(1)

    if not incoming:
        await conn.close()
        raise TimeoutError("⛔ No messages in queue")

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

        while True:
            try:
                audio_data = await websocket.receive_bytes()
                logger.info("🎧 Получено аудио от клиента")

                user_text = await asyncio.to_thread(service.asr.transcribe, audio_data)
                logger.info(f"💬 Распознанный текст: '{user_text}'")
                if not user_text:
                    continue
                try:
                    bot_reply = await asyncio.to_thread(
                        service.process_conversation,
                        user_input=user_text,
                        system_prompt=system_prompt,
                    )
                    logger.info(f"🤖 Ответ бота: '{bot_reply}'")
                except Exception as e:
                    logger.error(f"❌ Ошибка генерации ответа: {e}")

                    farewell = "Спасибо за звонок, до свидания!"
                    try:
                        await websocket.send_bytes(
                            await asyncio.to_thread(service.tts.synthesize, farewell)
                        )
                    except Exception as synth_err:
                        logger.error(f"❌ Ошибка при отправке финального сообщения: {synth_err}")

                    await websocket.send_text(json.dumps({"status": booking_failure_state}))
                    logger.info("🔔 Статус сессии: failed (из-за ошибки модели)")
                    await send_status_to_backend(
                        str(booking_info["booking_id"]), booking_failure_state
                    )
                    break

                status = service.extract_status(bot_reply)
                if status:
                    farewell = "Хорошо, спасибо! До свидания!"
                    await websocket.send_bytes(
                        await asyncio.to_thread(service.tts.synthesize, farewell)
                    )
                    logger.info("🔊 Отправлено финальное аудио")

                    await websocket.send_text(json.dumps({"status": status}))
                    logger.info(f"🔔 Статус сессии: {status}")
                    await send_status_to_backend(str(booking_info["booking_id"]), status)
                    break

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
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080, log_config=None)
