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


async def fetch_booking_info_from_queue(queue_name: str):
    """
    Connects to RabbitMQ, pulls one message off `queue_name`,
    acknowledges it, then fetches the full booking_data from the DB.
    """
    conn = await connect_robust(rabbitmq_url)
    chan = await conn.channel()
    await chan.set_qos(prefetch_count=1)
    queue = await chan.declare_queue(queue_name, durable=True)

    # get exactly one message
    incoming = await queue.get()
    data = json.loads(incoming.body)
    await incoming.ack()

    booking_id = data.get("booking_id")
    if not booking_id:
        raise ValueError("no booking_id in queue message")

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
                audio_data = await websocket.receive_bytes()
                user_text = await asyncio.to_thread(service.asr.transcribe, audio_data)

                bot_reply = await asyncio.to_thread(
                    service.process_conversation,
                    user_input=user_text,
                    system_prompt=system_prompt,
                )

                status = service.extract_status(bot_reply)
                if status:
                    farewell = "Хорошо, спасибо! До свидания!"
                    await websocket.send_bytes(
                        await asyncio.to_thread(service.tts.synthesize, farewell)
                    )
                    await websocket.send_text(json.dumps({"status": status}))
                    break

                history += f"<|user|>{user_text}<|assistant|>{bot_reply}\n"
                await websocket.send_bytes(
                    await asyncio.to_thread(service.tts.synthesize, bot_reply)
                )

            except WebSocketDisconnect:
                logger.warning("🔴 Client disconnected")
                break
            except Exception as e:
                logger.error(f"❌ Error in message loop: {e}")
                break

    except Exception as e:
        logger.error(f"⛔ Critical error before loop: {e}")
    finally:
        await websocket.close()
        logger.info("🛑 WebSocket closed")


@app.on_event("startup")
async def startup_event():

    asyncio.create_task(consume_queue(pars_queue, process_pars))
    logger.info("🚀 Background consumer for pars_queue started")


if __name__ == "__main__":
    import uvicorn
    import os
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    uvicorn.run(app, host="127.0.0.1", port=8000, log_config=None)
