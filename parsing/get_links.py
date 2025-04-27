from bs4 import BeautifulSoup
import time

# Configuration
BASE_FILE = "parsers/leclick/leclick.htm"
OUTPUT_FILE = "parsers/leclick/restaurant_links.txt"


def get_restaurant_links(url):
    with open(BASE_FILE, "r", encoding="utf-8") as leclick_file:
        while True:
            soup = BeautifulSoup(leclick_file, "html.parser")
            place_a = soup.find_all("a", class_="image", href=True)
            links = [a["href"] for a in place_a if a.get("href")]
            return links


all_restaurant_links = []

overall_start_time = time.time()

start_time = time.time()
first_page_links = get_restaurant_links(BASE_FILE)
end_time = time.time()
all_restaurant_links.extend(first_page_links)
print(
    f"Page parsed, {len(first_page_links)} links found in {end_time - start_time:.2f} seconds."
)

overall_end_time = time.time()
elapsed_time = overall_end_time - overall_start_time

with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
    for link in all_restaurant_links:
        file.write(f"{link}\n")

print(f"Total links found: {len(all_restaurant_links)}")
print(f"Total time taken: {elapsed_time:.2f} seconds")
