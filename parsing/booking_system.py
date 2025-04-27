from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time

USER_DATA = {
    "first_name": "Иван",
    "last_name": "Иванов",
    "email": "ivan@example.com",
    "phone": "9991234567",
    "persons": "4",
    "wishes": "Просьба поставить стол у окна",
    "time_value": "22:30",
}


def init_driver():
    chrome_options = Options()
    chrome_options.add_argument("--ignore-ssl-errors=yes")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=chrome_options
    )


def wait_for_element(driver, locator, timeout=20):
    return WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(locator))


def select_time(driver):
    try:
        # Кликаем на видимый элемент выбора времени
        time_picker = wait_for_element(
            driver, (By.CSS_SELECTOR, "div.leclick-time-select")
        )
        time_picker.click()
        time.sleep(0.5)

        # Выбираем нужное время из выпадающего списка
        option = wait_for_element(
            driver,
            (By.XPATH, f'//option[contains(@data-text, "{USER_DATA["time_value"]}")]'),
        )
        driver.execute_script("arguments[0].selected = true;", option)

        # Имитируем изменение через событие
        driver.execute_script(
            """
            var select = arguments[0];
            var event = new Event('change', {bubbles: true});
            select.dispatchEvent(event);
        """,
            time_picker.find_element(By.TAG_NAME, "select"),
        )

        print(f"✓ Время {USER_DATA['time_value']} выбрано успешно")
        return True
    except Exception as e:
        print(f"⚠️ Ошибка выбора времени: {str(e)}")
        return False


def select_persons(driver):
    try:
        # Открываем пикер выбора количества персон
        picker = wait_for_element(
            driver, (By.CSS_SELECTOR, "div.leclick-peopple-block-select")
        )
        picker.click()
        time.sleep(0.5)

        # Выбираем нужное количество
        person_option = wait_for_element(
            driver,
            (
                By.XPATH,
                f'//div[@class="peopleOption" and text()="{USER_DATA["persons"]}"]',
            ),
        )
        person_option.click()
        time.sleep(0.5)

        print(f"✓ Выбрано {USER_DATA['persons']} персоны")
        return True
    except Exception as e:
        print(f"⚠️ Ошибка выбора количества персон: {str(e)}")
        return False


def fill_booking_form():
    driver = init_driver()
    try:
        driver.get(
            "https://leclick.ru/restaurants/partner-reserve/id/13259/from/website?lang=ru"
        )
        time.sleep(2)

        # Исправленный блок заполнения полей
        fields = [
            (By.CSS_SELECTOR, "input.leclick-firstName", USER_DATA["first_name"]),
            (By.CSS_SELECTOR, "input.leclick-lastName", USER_DATA["last_name"]),
            (By.ID, "phone", USER_DATA["phone"]),
            (By.CSS_SELECTOR, "input.leclick-email", USER_DATA["email"]),
            (By.CSS_SELECTOR, "textarea.leclick-wishes", USER_DATA["wishes"]),
        ]

        # Правильная распаковка трех значений
        for by, selector, value in fields:
            element = wait_for_element(driver, (by, selector))
            element.clear()
            element.send_keys(value)
            time.sleep(0.3)

        # Выбор дополнительных параметров
        if not select_persons(driver):
            raise Exception("Не удалось выбрать количество персон")

        if not select_time(driver):
            raise Exception("Не удалось выбрать время")

        # Принимаем условия
        checkbox = wait_for_element(driver, (By.CSS_SELECTOR, "input#termsOfUse"))
        driver.execute_script("arguments[0].click();", checkbox)

        # Проверка заполнения
        time.sleep(2)
        print("✓ Все данные успешно заполнены!")

    except Exception as e:
        print(f"⛔ Критическая ошибка: {str(e)}")
        driver.save_screenshot("error.png")
    finally:
        driver.quit()


if __name__ == "__main__":
    fill_booking_form()
