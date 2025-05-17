from datetime import datetime
import io
import tempfile
import soundfile as sf
from voice_bot.models import TTSModel, ASRModel, LLMModel
import re
from config import booking_success_state, booking_failure_state


class VoiceBotService:
    def __init__(self):
        self.asr = ASRModel()
        self.llm = LLMModel()
        self.tts = TTSModel()

    def build_system_prompt(self, booking_info: dict) -> str:
        date_obj = booking_info["date"]

        date_word = date_obj.strftime("%Y-%m-%d")
        time_word = date_obj.strftime("%H:%M")
        return (
            "Ты — профессиональный голосовой бот по бронированию столиков в ресторанах. "
            "Говоришь только по‑русски.\n\n"
            f"Твоя цель: забронировать столик в ресторан: {booking_info['address']} на дату "
            f"{date_word} в {time_word} для {booking_info['people']} человек "
            f"на имя {booking_info['name']}.\n\n"
            " Ты уже назвал администратору всё данные теперь он будет уточнять у теб] что-то, твоя задча отвечать только то, что мы хотим заьронировать - предумывать ничего не надо"
            "Отвечай всегда кратко."
            # 'Если бронь подтверждена — скажи: "Спасибо, бронь подтверждена. Хорошего дня!"\n'
            # 'Если мест нет — скажи: "Хорошо, спасибо, я перезвоню в другой раз."\n'
            # "При непонятных ответах — повтори суть запроса.\n"
            f"ВАЖНО! если ты понимаешь, что тебе сказали, что стол смогли успешно забронировать, то верни дословно {booking_success_state}"
            f"ВАЖНО! если ты понимаешь, что тебе сказали, что стол ни как не смогут забронировать, то верни дословно {booking_failure_state}"
            "ТАКЖЕ не отвечай цифрами все цифры пиши буквами"
        )

    def number_to_words(self, num):
        if isinstance(num, str):
            try:
                num = int(num)
            except ValueError:
                return num

        units = [
            "ноль",
            "один",
            "два",
            "три",
            "четыре",
            "пять",
            "шесть",
            "семь",
            "восемь",
            "девять",
        ]
        teens = [
            "десять",
            "одиннадцать",
            "двенадцать",
            "тринадцать",
            "четырнадцать",
            "пятнадцать",
            "шестнадцать",
            "семнадцать",
            "восемнадцать",
            "девятнадцать",
        ]
        tens = [
            "",
            "",
            "двадцать",
            "тридцать",
            "сорок",
            "пятьдесят",
            "шестьдесят",
            "семьдесят",
            "восемьдесят",
            "девяносто",
        ]

        if 0 <= num < 10:
            return units[num]
        elif 10 <= num < 20:
            return teens[num - 10]
        elif 20 <= num < 100:
            return tens[num // 10] + (" " + units[num % 10] if num % 10 != 0 else "")
        else:
            return str(num)

    def time_to_words(self, time_str):
        try:
            hours, minutes = map(int, time_str.split(":"))

            hours_word = self.number_to_words(hours)
            minutes_word = self.number_to_words(minutes)

            return f"{hours_word} часов {minutes_word} минут"
        except:
            return time_str

    def date_to_words(self, date_str):
        months = {
            1: "января",
            2: "февраля",
            3: "марта",
            4: "апреля",
            5: "мая",
            6: "июня",
            7: "июля",
            8: "августа",
            9: "сентября",
            10: "октября",
            11: "ноября",
            12: "декабря",
        }

        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            day = date_obj.day
            month = date_obj.month

            month_word = months.get(month, str(month))
            day_word = self.number_to_words(day)
            return f"{day_word} {month_word}"
        except ValueError:
            return date_str

    def replace_numbers_in_text(self, text):
        def replace_match(match):
            num = match.group()
            return self.number_to_words(num)

        text = re.sub(r"\b\d+\b", replace_match, text)
        return text

    def generate_greeting(self, booking_info: dict) -> str:
        address = booking_info["address"]
        name = booking_info["name"]
        people = self.number_to_words(booking_info["people"])

        date_obj = booking_info["date"]

        date_word = self.date_to_words(date_obj.strftime("%Y-%m-%d"))
        time_word = self.time_to_words(date_obj.strftime("%H:%M"))

        return (
            f"Здравствуйте. Хочу забронировать столик в ресторан {address} "
            f"на {people} человек, {date_word} в {time_word}, "
            f"на имя {name}."
        )

    # def process_conversation(self, history: str, user_input: str, system_prompt: str) -> str:
    #     messages = [{"role": "system", "content": system_prompt}]

    #     if history:
    #         for part in history.strip().split("<|user|>")[1:]:
    #             user, assistant = part.split("<|assistant|>")
    #             messages.append({"role": "user", "content": user.strip()})
    #             messages.append({"role": "assistant", "content": assistant.strip()})

    #     messages.append({"role": "user", "content": user_input})

    #     prompt = self.llm.pipe.tokenizer.apply_chat_template(
    #         messages, tokenize=False, add_generation_prompt=True
    #     )

    #     return self.llm.generate_reply(prompt)

    # for TinyLlama
    def process_conversation_TL(self, user_input: str, system_prompt: str) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ]

        prompt = self.llm.pipe.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        return self.llm.generate_reply(prompt)

    def extract_status(self, text: str):
        tl = text.lower()
        if booking_failure_state.lower() in tl:
            return booking_failure_state
        if booking_success_state.lower() in tl:
            return booking_success_state

        return False

    def process_conversation(self, user_input: str, system_prompt: str) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ]
        return self.llm.generate_reply(messages)
