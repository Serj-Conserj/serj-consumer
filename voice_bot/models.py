import whisper
# from TTS.api import TTS
from transformers import pipeline
import torch
import io
import soundfile as sf
import numpy as np
import tempfile
import whisper
from typing import Optional
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()


class LLMModel:
    def __init__(self):
        print("[INIT] Preparing Groq API connection...")

    def generate_reply(self, prompt: str) -> str:
        url = "https://api.groq.com/openai/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {os.getenv('GROQ_TOKEN')}",
            "Content-Type": "application/json",
        }

        data = {
            "model": "llama3-70b-8192",
            "messages": prompt,
            "temperature": 0.7,
            "max_tokens": 1024,
            "top_p": 1,
            "stream": False,
        }

        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()
        except requests.RequestException as e:
            print(f"[ERROR] Request failed: {e}")
            return "Ошибка при получении ответа от модели."
        except (KeyError, IndexError) as e:
            print(f"[ERROR] Invalid response structure: {e}")
            return "Ошибка обработки ответа от модели."


class ASRModel:
    def __init__(self):
        print("[INIT] Loading ASR model...")
        self.model = whisper.load_model("base")

    def transcribe(self, audio_bytes: bytes, language: str = "ru") -> str:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as f:
            f.write(audio_bytes)
            f.flush()

            result = self.model.transcribe(
                f.name,
                language=language,
                task="transcribe",
                fp16=False,
                verbose=False,
                temperature=0.0,
                best_of=5,
                beam_size=5,
            )

        text = result["text"].strip()

        text = self._postprocess_text(text)
        return text

    def _postprocess_text(self, text: str) -> str:
        """Постобработка распознанного текста"""
        text = text.replace("...", "").strip()
        if text and len(text) > 1:
            text = text[0].upper() + text[1:]
        return text


class LLMModel_TinyLlama:
    def __init__(self):
        print("[INIT] Loading TinyLlama...")
        self.pipe = pipeline(
            "text-generation",
            model="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
            torch_dtype="auto",
            device_map="auto",
        )

    def generate_reply(self, prompt: str) -> str:
        out = self.pipe(
            prompt,
            max_new_tokens=150,
            do_sample=True,
            temperature=0.7,
            top_p=0.95,
            return_full_text=False,
        )
        return out[0]["generated_text"].strip()


class TTSModel:
    def __init__(self):

        torch.backends.quantized.engine = "none"
        torch.set_num_threads(4)

        self.device = torch.device("cpu")
        self.language = "ru"
        self.model_id = "v4_ru"
        self.sample_rate = 48000
        self.speaker = "xenia"

        self.model, self.example_text = torch.hub.load(
            repo_or_dir="snakers4/silero-models",
            model="silero_tts",
            language=self.language,
            speaker=self.model_id,
        )
        self.model.to(self.device)

    def synthesize(self, text, speaker=None):
        """Генерация аудио с возможностью смены голоса"""
        audio = self.model.apply_tts(
            text=text, speaker=speaker or self.speaker, sample_rate=self.sample_rate
        )

        audio_np = audio.numpy()

        with io.BytesIO() as wav_buffer:
            sf.write(wav_buffer, audio_np, self.sample_rate, format="WAV")
            wav_bytes = wav_buffer.getvalue()

        return wav_bytes
