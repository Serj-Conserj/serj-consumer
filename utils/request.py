import httpx


async def send_status_to_backend(booking_id, status):
    try:
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
    except Exception as e:
        print(f"❌ Ошибка при обновлении статуса после сбоя: {e}")
