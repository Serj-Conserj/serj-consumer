import requests
from bs4 import BeautifulSoup
import json

INPUT_FILE = "parsers/leclick/restaurant_links.txt"
HTML_FILE = "parsers/leclick/leclick.htm"
OUTPUT_FILE = "parsers/leclick/restaurant_data_leclick_1.json"
TIMEOUT = 3

BASE_HEADERS = {
    "Accept": "text/html, */*; q=0.01",  # '*/*'
    "Sec-Fetch-Site": "same-origin",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Sec-Fetch-Mode": "cors",
    "Host": "leclick.ru",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Connection": "keep-alive",
    "Referer": "",
    "Sec-Fetch-Dest": "empty",
    "X-Requested-With": "XMLHttpRequest",
}
PARAMS = {
    "ajax": "1",
}


def extract_data_from_html_file(html_file):
    try:
        with open(html_file, "r", encoding="utf-8") as file:
            html_content = file.read()

        soup = BeautifulSoup(html_content, "html.parser")

        restaurant_data = []

        rest_cards = soup.find_all("div", class_="restCard")

        for rest_card in rest_cards:
            alternate_name_span = rest_card.find("span", class_="rest-card__fav-icon")
            goo_rating_div = rest_card.find("div", class_="restRate")

            alternate_name = (
                alternate_name_span["data-name"]
                if alternate_name_span and "data-name" in alternate_name_span.attrs
                else None
            )

            goo_rating = None
            if goo_rating_div:
                rating_span = goo_rating_div.find("span")
                if rating_span:
                    goo_rating = rating_span.get_text(strip=True)

            restaurant_data.append(
                {"alternate_name": alternate_name, "goo_rating": goo_rating}
            )

        return restaurant_data

    except Exception as e:
        print(f"Error while processing HTML file: {e}")
        return None


def extract_restaurant_data(url, data, data_count):
    try:
        response = requests.get(url, timeout=TIMEOUT, headers=BASE_HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        response_for_booking = requests.get(
            url + "/booking", timeout=TIMEOUT, params=PARAMS, headers=BASE_HEADERS
        )
        soup_for_booking = BeautifulSoup(response_for_booking.content, "html.parser")

        full_name = soup.find("h1", style="max-width: 550px")
        address = soup.find("span", class_="address")
        close_metro_div = soup.find("div", class_="metro")
        kitchen_div = soup.find("div", class_="items kitchens")

        booking_form_tag = soup_for_booking.find("iframe", class_="lckBookingForm")
        booking_form = (
            "https://leclick.ru" + booking_form_tag["src"] if booking_form_tag else None
        )

        metro_list = None
        if close_metro_div:
            metro_list = [
                metro.strip()
                for metro in close_metro_div.get_text(strip=True).split(",")
                if metro.strip()
            ]

        cuisines = []
        if kitchen_div:
            kitchen_spans = kitchen_div.find_all("span", class_="kitchen")
            for span in kitchen_spans:
                links = span.find_all("a")
                for link in links:
                    cuisines.append(link.get_text(strip=True))

        return {
            "full_name": full_name.get_text(strip=True) if full_name else None,
            "alternate_name": data[data_count]["alternate_name"]
            if data[data_count]["alternate_name"]
            else None,
            "address": address.get_text(strip=True) if address else None,
            "close_metro": metro_list if metro_list else None,
            "main_cuisine": cuisines if cuisines else None,
            "goo_rating": data[data_count]["goo_rating"]
            if data[data_count]["goo_rating"]
            else None,
            "party_booking_name": url,
            "booking_form": booking_form,
        }
    except requests.RequestException as e:
        print(f"Error while requesting {url}: {e}")
        return None


def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        urls = [line.strip() for line in file]

    all_restaurant_data = []

    data_html = extract_data_from_html_file(HTML_FILE)
    data_count = -1

    for url in urls:
        data_count += 1
        data = extract_restaurant_data(url, data_html, data_count)
        if data:
            all_restaurant_data.append(data)
            print(f"Data extracted from {url}: {data}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(all_restaurant_data, file, ensure_ascii=False, indent=4)

    print(f"Total records found: {len(all_restaurant_data)}")


if __name__ == "__main__":
    main()
