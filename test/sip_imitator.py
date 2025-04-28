"""
Admin Simulator
===============

Подключается к VoiceBot FastAPI (ws://localhost:8000/ws?...) и имитирует
разговор администратора:
1. Получает голос бота, сохраняет и проигрывает.
2. Ждёт, чтобы вы ввели текст ответа администратора.
3. Синтезирует этот текст в речь (TTS) и отправляет обратно боту.
4. Цикл продолжается, пока бот не завершит соединение.

Usage:
------
python admin.py --address "Москва, ул. Тверская 7" --date 2025-05-01 --time 19:00 --people 2 --name Сергей
"""

import argparse
import asyncio
import tempfile
import io
from pathlib import Path
import time
import torch
import torchaudio
import soundfile as sf
import simpleaudio as sa
import websockets

class TTSModel:
    def __init__(self):
        torch.backends.quantized.engine = "none"
        torch.set_num_threads(4)

        self.device = torch.device("cpu")
        self.language = "ru"
        self.model_id = "v4_ru"
        self.sample_rate = 48000
        self.speaker = "xenia"

        self.model, _ = torch.hub.load(
            repo_or_dir="snakers4/silero-models",
            model="silero_tts",
            language=self.language,
            speaker=self.model_id,
        )
        self.model.to(self.device)

    def synthesize(self, text, speaker=None):
        """Генерация аудио с возможностью смены голоса"""
        audio = self.model.apply_tts(
            text=text, 
            speaker=speaker or self.speaker, 
            sample_rate=self.sample_rate
        )
        
        # Convert torch tensor to numpy array
        audio_np = audio.cpu().numpy()
        
        # Convert to bytes
        with io.BytesIO() as wav_buffer:
            sf.write(wav_buffer, audio_np, self.sample_rate, format='WAV')
            wav_bytes = wav_buffer.getvalue()
            
        return wav_bytes

# Initialize TTS model
TTS_ENGINE = TTSModel()

async def admin_chat(uri: str):
    async with websockets.connect(uri) as ws:
        print(
            "[ADMIN] Подключились к боту. Введите ответ администратора, чтобы начать диалог."
        )

        while True:
            # 1) Получаем аудио от бота
            try:
                bot_audio = await ws.recv()
            except websockets.exceptions.ConnectionClosedOK:
                print("[ADMIN] Бот завершил соединение.")
                break
            except websockets.exceptions.ConnectionClosedError as e:
                print("[ADMIN] Соединение закрыто с ошибкой:", e)
                break

            # 2) Сохраняем и играем
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(bot_audio)
                tmp_path = Path(tmp.name)
            wave_obj = sa.WaveObject.from_wave_file(str(tmp_path))
            play_obj = wave_obj.play()
            play_obj.wait_done()
            tmp_path.unlink(missing_ok=True)

            # 3) Ждём ввода администратора
            admin_text = input(
                "Ответ администратора (пустая строка — закончить): "
            ).strip()
            if not admin_text:
                print("[ADMIN] Завершение теста.")
                break

            # 4) Синтезируем TTS и отправляем
            wav_bytes = TTS_ENGINE.synthesize(admin_text)
            await ws.send(wav_bytes)
            time.sleep(1)  # лёгкая пауза между репликами


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", default=8080)
    args = parser.parse_args()

    ws_uri = f"ws://{args.host}:{args.port}/ws"

    asyncio.run(admin_chat(ws_uri))