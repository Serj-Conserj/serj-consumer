# from bs4 import BeautifulSoup
# import time

# # Configuration
# BASE_FILE = "parsers/leclick/leclick.htm"
# OUTPUT_FILE = "parsers/leclick/restaurant_links.txt"

# def get_restaurant_links(url):
#     with open(BASE_FILE, 'r', encoding='utf-8') as leclick_file:
#         while True:
#             soup = BeautifulSoup(leclick_file, 'html.parser')
#             place_a = soup.find_all('a', class_='image', href=True)
#             links = [a['href'] for a in place_a if a.get('href')]
#             return links

# all_restaurant_links = []

# overall_start_time = time.time()

# start_time = time.time()
# first_page_links = get_restaurant_links(BASE_FILE)
# end_time = time.time()
# all_restaurant_links.extend(first_page_links)
# print(f"Page parsed, {len(first_page_links)} links found in {end_time - start_time:.2f} seconds.")

# overall_end_time = time.time()
# elapsed_time = overall_end_time - overall_start_time

# with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
#     for link in all_restaurant_links:
#         file.write(f"{link}\n")

# print(f"Total links found: {len(all_restaurant_links)}")
# print(f"Total time taken: {elapsed_time:.2f} seconds")


from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager

# Остальные импорты остаются без изменений
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Настройки
URL = 'https://leclick.ru/restaurants/index'
OUTPUT_FILE = 'restaurants.txt'
MAX_WAIT = 10
SCROLL_PAUSE = 1

# Инициализация Firefox с автоматической установкой драйвера
service = Service(GeckoDriverManager().install())
driver = webdriver.Firefox(service=service)

# Остальной код остается без изменений
driver.get(URL)
restaurant_links = set()

def scroll_to_bottom():
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(SCROLL_PAUSE)
        new_height = driver.execute_script("return document.body.scrollHeight")
        
        if new_height == last_height:
            break
        last_height = new_height

try:
    while True:
        WebDriverWait(driver, MAX_WAIT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a.image"))
        )
        
        links = driver.find_elements(By.CSS_SELECTOR, 'a.image[href^="/restaurant/"]')
        for link in links:
            href = link.get_attribute('href')
            if href and href not in restaurant_links:
                restaurant_links.add(href)
                print(f"Найдено: {href}")
        
        prev_count = len(links)
        scroll_to_bottom()
        
        new_links = driver.find_elements(By.CSS_SELECTOR, 'a.image[href^="/restaurant/"]')
        if len(new_links) == prev_count:
            print("Завершаем сбор данных...")
            break

except Exception as e:
    print(f"Ошибка: {str(e)}")
finally:
    driver.quit()

with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    for link in restaurant_links:
        f.write(f"{link}\n")

print(f"Собрано {len(restaurant_links)} ссылок. Файл: {OUTPUT_FILE}")
