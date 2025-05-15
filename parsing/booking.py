from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager
from config import booking_success_state, booking_failure_state
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    TimeoutException,
)
from datetime import datetime
import time, re

TIME_RE = re.compile(r"^\d{1,2}:\d{2}$")


def to_user_data(row: dict) -> dict:
    dt = row["date"]
    return {
        "first_name": row["name"],
        "phone": row["phone"],
        "persons": str(row["people"]),
        "wishes": row.get("special_requests", "") or "",
        "date_value": dt.strftime("%Y-%m-%d"),
        "time_value": dt.strftime("%H:%M"),
        "url": row["url"],
    }


# ──────────────────────────────────────────────────────────────────────────────
#                               КЛИЕНТ-БРОНИРОВЩИК
# ──────────────────────────────────────────────────────────────────────────────
class BookingClient:
    def __init__(self, user_data: dict, link: str):
        self.data = user_data
        self.link = link
        self.driver = self._init_driver()

    # ---------- настройка браузера ----------
    @staticmethod
    def _init_driver() -> webdriver.Remote:
        opt = Options()
        opt.headless = True  # включи, если нужен headless
        opt.set_preference("permissions.default.geo", 2)
        opt.set_preference("geo.enabled", False)
        opt.set_preference("dom.webnotifications.enabled", False)
        opt.set_preference("dom.webdriver.enabled", False)
        opt.set_preference("useAutomationExtension", False)
        opt.set_capability("acceptInsecureCerts", True)

        return webdriver.Remote(
            command_executor="http://selenium:4444/wd/hub",
            options=opt
        )

    # ---------- утилита ожидания ----------
    def _wait_click(self, locator, to=20):
        return WebDriverWait(self.driver, to).until(EC.element_to_be_clickable(locator))

    # ---------- выбор даты ----------
    def select_date(self) -> bool:
        wanted = datetime.strptime(self.data["date_value"], "%Y-%m-%d")
        wanted_day = str(wanted.day)
        try:
            self._wait_click((By.CSS_SELECTOR, "div.leclick-date-select")).click()
            time.sleep(0.3)
            day_btn = self.driver.find_element(
                By.XPATH,
                f'//div[contains(@class,"DayPicker") or contains(@class,"calendar")]'
                f'//button[normalize-space()="{wanted_day}" and not(@disabled)]',
            )
            try:
                day_btn.click()
            except ElementClickInterceptedException:
                self.driver.execute_script("arguments[0].click();", day_btn)
            print("[PARS] ✅ Дата выбрана вручную")
            return True
        except (TimeoutException, ElementClickInterceptedException):
            print("[PARS] ❗ Не удалось кликнуть дату — пробуем через JS (Flatpickr)")
            try:
                self.driver.execute_script(
                    """
                    const inp = document.querySelector('input.leclick-date');
                    if (inp && inp._flatpickr) {
                        inp._flatpickr.setDate(arguments[0], true);
                    }
                    """,
                    self.data["date_value"]
                )
                time.sleep(5)  # дать время обновиться
                print("[PARS] ✅ Дата выставлена через Flatpickr")
                return True
            except Exception as e:
                print("[PARS] ⛔ Ошибка выставления даты через JS:", e)
                return False

    # ---------- выбор персон ----------
    def select_persons(self) -> bool:
        try:
            self._wait_click(
                (By.CSS_SELECTOR, "div.leclick-peopple-block-select")
            ).click()
            time.sleep(0.2)
            self._wait_click(
                (
                    By.XPATH,
                    f'//div[@class="peopleOption" and text()="{self.data["persons"]}"]',
                )
            ).click()
            return True
        except Exception as e:
            return False

    # ---------- выбор времени ----------
    def select_time(self) -> bool:
        try:
            picker = self._wait_click((By.CSS_SELECTOR, "div.leclick-time-select"))
            picker.click()
            time.sleep(0.25)
            opts = [
                o
                for o in picker.find_elements(By.TAG_NAME, "option")
                if TIME_RE.match(o.get_attribute("data-text") or "")
            ]
            print("[PARS] Время:", [o.get_attribute("data-text") for o in opts], opts)
            if not opts:
                raise RuntimeError("Нет валидных времён HH:MM")
            
            fmt = "%H:%M"
            want = datetime.strptime(self.data["time_value"], fmt)
            print("[PARS] want:", want)
            best = min(
                opts,
                key=lambda o: abs(
                    (
                        datetime.strptime(o.get_attribute("data-text"), fmt) - want
                    ).total_seconds()
                ),
            )
            self.driver.execute_script("arguments[0].selected=true;", best)
            self.driver.execute_script(
                "arguments[0].parentElement.dispatchEvent(new Event('change',{bubbles:true}));",
                best,
            )
            return True
        except Exception as e:
            return False

    # ---------- основной процесс ----------
    def run(self):
        try:
            self.driver.get(self.link)
            time.sleep(2)

            # текстовые поля
            for by, sel, val in (
                (By.CSS_SELECTOR, "input.leclick-firstName", self.data["first_name"]),
                (By.ID, "phone", self.data["phone"]),
                (By.CSS_SELECTOR, "textarea.leclick-wishes", self.data["wishes"]),
            ):
                el = self._wait_click((by, sel))
                el.clear()
                el.send_keys(val)
                time.sleep(0.15)

            if not self.select_persons():
                raise RuntimeError("persons fail")
            if not self.select_date():
                raise RuntimeError("date fail")
            
            if not self.select_time():
                raise RuntimeError("time fail")

            self.driver.execute_script(
                "document.querySelector('input#termsOfUse').click();"
            )
            print("[PARS] ✓ Форма заполнена и готова к отправке")
            # self._wait_click((By.CSS_SELECTOR,'button.leclick-submit')).click() # создание брони

            time.sleep(2)

            return {
                "status": booking_success_state,
            }
        except Exception as e:
            raise RuntimeError("❌ Ошибка бронирования парсингом")
        finally:
            self.driver.quit()
        return {
            "status": booking_failure_state,
        }


# ──────────────────────────────────────────────────────────────────────────────
#                                Публичная точка входа
# ──────────────────────────────────────────────────────────────────────────────
# def book_table(user_data: dict):
#     user_data = to_user_data(user_data)
#     try:
#         link = user_data.pop("url", None)
#         if not link:
#             raise ValueError("[PARS] ❌ Не указана ссылка на бронь")
#         resp = BookingClient(user_data, link).run()
#         return resp
#     except Exception as e:
#         print("[PARS] ⛔  Ошибка бронирования:", e)
#         raise RuntimeError(
#             "[PARS] ❌ Бронирование парсингом не получилось, попробуем звонок"
#         )
def book_table(user_data: dict):
    print("[PARS] 📥 Входящие данные:", user_data)
    user_data = to_user_data(user_data)
    try:
        link = user_data.pop("url", None)
        if not link:
            raise ValueError("[PARS] ❌ Не указана ссылка на бронь")
        print("[PARS] 🔗 Ссылка:", link)
        resp = BookingClient(user_data, link).run()
        print("[PARS] ✅ Ответ:", resp)
        return resp
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("[PARS] ⛔ Ошибка бронирования:", e)
        raise RuntimeError(
            "[PARS] ❌ Бронирование парсингом не получилось, попробуем звонок"
        )

# ───────────────────────────── локальный тест ────────────────────────────────
if __name__ == "__main__":
    demo = {
        "first_name": "Иван",
        "phone": "9991234567",
        "persons": "4",
        "wishes": "Просьба у окна",
        "date_value": "2025-05-08",
        "time_value": "22:13",
    }
    demo_link = (
        "https://leclick.ru/restaurants/partner-reserve/id/13259/from/website?lang=ru"
    )
    book_table(demo, demo_link)
