# import requests
# from bs4 import BeautifulSoup
# import json

# INPUT_FILE = "parsers/leclick/restaurant_links.txt"
# HTML_FILE = "parsers/leclick/leclick.htm"
# OUTPUT_FILE = "parsers/leclick/restaurant_data_leclick_1.json"
# TIMEOUT = 3

# BASE_HEADERS = {
#     'Accept': 'text/html, */*; q=0.01', # '*/*'
#     'Sec-Fetch-Site': 'same-origin',
#     'Accept-Language': 'en-US,en;q=0.9',
#     'Accept-Encoding': 'gzip, deflate, br',
#     'Sec-Fetch-Mode': 'cors',
#     'Host': 'leclick.ru',
#     'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15',
#     'Connection': 'keep-alive',
#     'Referer': '',
#     'Sec-Fetch-Dest': 'empty',
#     'X-Requested-With': 'XMLHttpRequest',
# }
# PARAMS = {
#     'ajax': '1',
# }

# def extract_data_from_html_file(html_file):
#     try:
#         with open(html_file, "r", encoding="utf-8") as file:
#             html_content = file.read()

#         soup = BeautifulSoup(html_content, 'html.parser')

#         restaurant_data = []
        
#         rest_cards = soup.find_all('div', class_='restCard')

#         for rest_card in rest_cards:
#             alternate_name_span = rest_card.find('span', class_='rest-card__fav-icon')
#             goo_rating_div = rest_card.find('div', class_='restRate')

#             alternate_name = alternate_name_span['data-name'] if alternate_name_span and 'data-name' in alternate_name_span.attrs else None
            
#             goo_rating = None
#             if goo_rating_div:
#                 rating_span = goo_rating_div.find('span')
#                 if rating_span:
#                     goo_rating = rating_span.get_text(strip=True)

#             restaurant_data.append({
#                 'alternate_name': alternate_name,
#                 'goo_rating': goo_rating
#             })

#         return restaurant_data
        
#     except Exception as e:
#         print(f"Error while processing HTML file: {e}")
#         return None


# def extract_restaurant_data(url, data, data_count):
#     try:
#         response = requests.get(url, timeout=TIMEOUT, headers=BASE_HEADERS)
#         response.raise_for_status()
#         soup = BeautifulSoup(response.content, 'html.parser')
        
#         response_for_booking = requests.get(url + "/booking", timeout=TIMEOUT, params=PARAMS, headers=BASE_HEADERS)
#         soup_for_booking = BeautifulSoup(response_for_booking.content, 'html.parser')
        
#         full_name = soup.find('h1', style='max-width: 550px')
#         address = soup.find('span', class_='address')
#         close_metro_div = soup.find('div', class_='metro')
#         kitchen_div = soup.find('div', class_='items kitchens')
        
#         booking_form_tag = soup_for_booking.find('iframe', class_='lckBookingForm')
#         booking_form = 'https://leclick.ru' + booking_form_tag['src'] if booking_form_tag else None

#         metro_list = None
#         if close_metro_div:
#             metro_list = [metro.strip() for metro in close_metro_div.get_text(strip=True).split(',') if metro.strip()]
            
#         cuisines = []
#         if kitchen_div:
#             kitchen_spans = kitchen_div.find_all('span', class_='kitchen')
#             for span in kitchen_spans:
#                 links = span.find_all('a')
#                 for link in links:
#                     cuisines.append(link.get_text(strip=True))
        

#         return {
#             'full_name': full_name.get_text(strip=True) if full_name else None,
#             'alternate_name': data[data_count]["alternate_name"] if data[data_count]["alternate_name"] else None,
#             'address': address.get_text(strip=True) if address else None,
#             'close_metro': metro_list if metro_list else None,
#             'main_cuisine': cuisines if cuisines else None,
#             'goo_rating': data[data_count]["goo_rating"] if data[data_count]["goo_rating"] else None, 
#             'party_booking_name': url,
#             'booking_form': booking_form,
#         }
#     except requests.RequestException as e:
#         print(f"Error while requesting {url}: {e}")
#         return None

# def main():
#     with open(INPUT_FILE, "r", encoding="utf-8") as file:
#         urls = [line.strip() for line in file]

#     all_restaurant_data = []

#     data_html = extract_data_from_html_file(HTML_FILE)
#     data_count = -1

#     for url in urls:
#         data_count += 1
#         data = extract_restaurant_data(url, data_html, data_count)
#         if data:
#             all_restaurant_data.append(data)
#             print(f"Data extracted from {url}: {data}")

#     with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
#         json.dump(all_restaurant_data, file, ensure_ascii=False, indent=4)

#     print(f"Total records found: {len(all_restaurant_data)}")

# if __name__ == "__main__":
#     main()



import json
import re
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
from urllib.parse import urljoin, urlparse, unquote

class RestaurantParser:
    def __init__(self, html, full_url):
        self.soup = BeautifulSoup(html, 'html.parser')
        self.full_url = full_url
        self.base_url = f"{urlparse(full_url).scheme}://{urlparse(full_url).netloc}"

    def get_restaurant_id(self):
        try:
            # Ищем элемент с классом rest-fav-bl и извлекаем data-id
            fav_block = self.soup.find('div', class_='rest-fav-bl')
            if fav_block and fav_block.has_attr('data-id'):
                return fav_block['data-id']
            
            # Фолбек для старых версий (если потребуется)
            legacy_div = self.soup.find('div', {'data-restaurant-id': True})
            return legacy_div['data-restaurant-id'] if legacy_div else None
            
        except Exception as e:
            print(f"Error getting restaurant id: {str(e)}")
            return None

    def get_names(self):
        names = {
            'main': None,
            'alternate': []
        }
        
        try:
            # 1. Извлечение из URL
            url_path = urlparse(self.full_url).path
            if '/restaurant/' in url_path:
                slug = unquote(url_path.split('/restaurant/')[-1].split('/')[0])
                name_from_url = ' '.join(
                    part.capitalize() for part in slug.replace('-', ' ').split()
                )
                names['alternate'].append(name_from_url)
            
            # 2. Из data-атрибута
            alternate_name_span = self.soup.find('span', class_='rest-card__fav-icon')
            if alternate_name_span and 'data-name' in alternate_name_span.attrs:
                names['alternate'].append(alternate_name_span['data-name'].strip())
            
            # 3. Из заголовка
            title_text = self.soup.select_one('.restTitle h1')
            if title_text:
                title_parts = title_text.text.strip().split('/')
                names['main'] = title_parts[0].strip()
                if len(title_parts) > 1:
                    names['alternate'].extend(
                        [p.strip() for p in title_parts[1:] if p.strip()]
                    )
            
            names['alternate'] = list(
                {name for name in names['alternate'] if name and name != names['main']}
            )
            
        except Exception as e:
            print(f"Error parsing names: {str(e)}")
        
        return names

    def get_phone(self):
        try:
            return self.soup.select_one('.phone-click').text.strip()
        except AttributeError:
            return None

    def get_address(self):
        try:
            return self.soup.select_one('.address .address').text.strip()
        except AttributeError:
            return None

    def get_metro(self):
        try:
            metro_text = self.soup.select_one('.metro').text.strip()
            return [m.strip() for m in metro_text.split(',')]
        except AttributeError:
            return []

    def get_type(self):
        try:
            return self.soup.select_one('.restType').text.strip()
        except AttributeError:
            return None

    def get_average_check(self):
        try:
            check_block = self.soup.find('div', class_='importantInfo').find(
                'span', string='Средний чек:'
            ).find_parent('div', class_='items')
            
            check_text = check_block.get_text(strip=True).replace('Средний чек:', '')
            
            if '—' in check_text or '-' in check_text:
                return check_text.replace('—', '-').strip()
            return int(re.sub(r'\D', '', check_text))
        except (AttributeError, ValueError, TypeError):
            return None

    def get_cuisines(self):
        try:
            return [a.text.strip() for a in self.soup.select('.kitchen a')]
        except AttributeError:
            return []

    def get_opening_hours(self):
        hours = {}
        days_map = {
            'd0': 'ВС', 'd1': 'ПН', 'd2': 'ВТ',
            'd3': 'СР', 'd4': 'ЧТ', 'd5': 'ПТ', 'd6': 'СБ'
        }
        
        for day in self.soup.select('[class^="item d"]'):
            class_name = [c for c in day['class'] if c.startswith('d')][0]
            time_from = day.select_one('.timeFrom')
            time_to = day.select_one('.timeTo')
            
            if time_from and time_to:
                hours[days_map[class_name]] = f"{time_from.text.strip()} - {time_to.text.strip()}"
            else:
                hours[days_map[class_name]] = 'весь день'
        
        return hours

    def get_menu_links(self):
        menus = {}
        try:
            for link in self.soup.select('.goToMenu'):
                menu_type = link.text.strip()
                url = link['href']
                menus[menu_type] = url
        except AttributeError:
            pass
        return menus

    def get_photos(self):
        # Группируем фото по типам
        photos = {'interior': [], 'food': [], 'facade': []}
        for a in self.soup.select('a[type]'):
            photo_type = a['type']
            if photo_type in photos:
                photos[photo_type].append(a['href'])
        return photos

    def get_coordinates(self):
        try:
            map_element = self.soup.select_one('.mapAction')
            return {
                'lat': float(map_element['data-lat']),
                'lon': float(map_element['data-long'])
            }
        except (AttributeError, KeyError):
            return None

    def get_booking_links(self):
        booking_links = {}
        restraunt_id = self.get_restaurant_id()
        try:
            # Основное бронирование
            main_booking = self.soup.select_one('.bookingBtn.mainBooking a')
            if main_booking:
                # full_url = urljoin(self.base_url, main_booking['href'])
                booking_links['main'] = f"https://leclick.ru/restaurants/partner-reserve/id/{restraunt_id}/from/website?lang=ru"

            # Бронирование банкета
            banquet_booking = self.soup.select_one('.bookingBtn a[href*="banquet=1"]')
            if banquet_booking:
                # full_url = urljoin(self.base_url, banquet_booking['href'])
                booking_links['banquet'] = f"https://leclick.ru/restaurants/partner-reserve/id/{restraunt_id}/from/website?banquet=1&lang=ru"
        except Exception as e:
            print(f"Error getting booking links: {str(e)}")
        return booking_links

    def get_deposit_rules(self):
        try:
            deposit_rules = self.soup.select_one('.depositRulesText pre').text.strip()
            return deposit_rules.replace('\n', ' ')
        except AttributeError:
            return None

    def get_visit_purposes(self):
        try:
            purpose_block = self.soup.find('div', class_='importantInfo').find(
                'span', string='Цель посещения:'
            ).find_parent('div', class_='items')
            
            return [a.text.strip() for a in purpose_block.select('a')]
        except AttributeError:
            return []

    def get_features(self):
        try:
            features_block = self.soup.find('div', class_='importantInfo').find(
                'span', string='Особенности:'
            ).find_parent('div', class_='items')
            
            return [
                a.text.strip() 
                for a in features_block.select('a:not(.hidden)')
                if a.text.strip()
            ]
        except AttributeError:
            return []

    def get_reviews(self):
        reviews = []
        try:
            for review in self.soup.select('.feedback .item'):
                review_data = {
                    'author': review.select_one('.name').text.strip(),
                    'date': review.select_one('.date').text.strip(),
                    'rating': len(review.select('.material-icons:not(.md-18)')),
                    'text': review.select_one('.review').text.strip() if review.select_one('.review') else None,
                    'source': review.select_one('.partner').text.strip() if review.select_one('.partner') else None
                }
                reviews.append(review_data)
        except Exception as e:
            print(f"Error parsing reviews: {str(e)}")
        return reviews

    def parse(self):
        names = self.get_names()
        data = {
            'full_name': names['main'],
            'alternate_name': names['alternate'],
            'phone': self.get_phone(),
            'address': self.get_address(),
            'close_metro': self.get_metro(),
            'type': self.get_type(),
            'average_check': self.get_average_check(),
            'main_cuisine': self.get_cuisines(),
            'opening_hours': self.get_opening_hours(),
            'menu_links': self.get_menu_links(),
            'photos': self.get_photos(),
            'coordinates': self.get_coordinates(),
            'features': {
                'online_booking': 'принимает' if 'Забронировать' in self.soup.text else 'не принимает'
            },
            'booking_links': self.get_booking_links(),
            'deposit_rules': self.get_deposit_rules(),
            'visit_purposes': self.get_visit_purposes(),
            'features': self.get_features(),
            'reviews': self.get_reviews(),
            'description': self.get_full_description()
        }
        return data

    def get_full_description(self):
        try:
            full_desc = self.soup.select_one('#allDescr')
            if full_desc:
                return full_desc.text.strip()
            
            short_desc = self.soup.select_one('#shortDescr')
            if short_desc:
                return short_desc.text.strip()
            
            return self.soup.select_one('.description .text').text.strip()
        except AttributeError:
            return None

def main():
    start_time = time.time()
    start_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"Script started at: {start_dt}")
    
    try:
        with open('restaurants test.txt', 'r') as f: # restaurants test.txt for test, restaurants.txt for prod
            urls = f.read().splitlines()
        
        results = []
        
        with tqdm(total=len(urls), desc="Processing") as pbar:
            for url in urls:
                try:
                    response = requests.get(url, timeout=15)
                    response.raise_for_status()
                    
                    parser = RestaurantParser(response.text, url)
                    data = parser.parse()
                    
                    data['source'] = {
                        'url': url,
                        'domain': urlparse(url).netloc
                    }
                    
                    results.append(data)
                    
                except Exception as e:
                    print(f"\nError processing {url}: {str(e)}")
                finally:
                    pbar.update(1)
        
        with open('restaurants test.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        print(f"Fatal error: {str(e)}")
    
    # Тайминг выполнения
    end_time = time.time()
    elapsed = end_time - start_time
    print(f"\nTotal execution time: {elapsed:.2f} seconds")
    print(f"Average per page: {elapsed/len(urls):.2f} seconds")

if __name__ == '__main__':
    main()
