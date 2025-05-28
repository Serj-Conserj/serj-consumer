import httpx
from utils.logger import logger  

async def send_status_to_backend(booking_id, status):
    try:
        logger.info(f"📡 Отправка статуса {status} для booking_id={booking_id}")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://conserj.ru/api/bookings/update_status",
                json={
                    "booking_id": booking_id,
                    "status": status,
                },
                timeout=5,
            )
            response.raise_for_status()
        logger.info(f"✅ Статус {status} успешно отправлен для booking_id={booking_id}")
    except Exception as e:
        logger.error(f"❌ Ошибка при обновлении статуса после сбоя: {e}")
