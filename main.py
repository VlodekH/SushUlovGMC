import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from datetime import datetime
import json
import hashlib
import time
import os
import re

# --- KONFIGURACJA ---
BASE_URL = "https://sushi-ulov.pl"
URL_TO_PARSE = "https://sushi-ulov.pl/menu/"

# Prefiks sekcji menu dla budowania linków
URL_PREFIX = "section:menu-545"

# Ścieżka zapisu (Docker vs Local)
if os.path.exists("/data"):
    OUTPUT_FILE = "/data/feed.xml"
else:
    OUTPUT_FILE = "feed.xml"


def clean_price(price_input):
    """
    Formatuje cenę. Dzieli przez 100, bo baza zwraca grosze (4700 -> 47.00).
    """
    if price_input is None: return "0.00"

    val = str(price_input)
    clean_str = re.sub(r'[^\d]', '', val)

    if not clean_str: return "0.00"

    try:
        float_val = float(clean_str)
        final_price = float_val / 100
        return f"{final_price:.2f}"
    except ValueError:
        return "0.00"


def get_availability(is_available):
    """Konwersja dostępności na format Google"""
    if is_available is True:
        return "in stock"
    return "out of stock"


def get_google_category_id(category_name):
# sources: https://www.google.com/basepages/producttype/taxonomy-with-ids.en-US.txt; https://www.google.com/basepages/producttype/taxonomy-with-ids.pl-PL.txt
    if not category_name:
        return "5814"

    cat_lower = category_name.lower()

    if "sos" in cat_lower:
        return "427"

    if "woda" in cat_lower or "napój" in cat_lower or "napoje" in cat_lower:
        return "420"

    return "5814"


def run_parser():
    print(f"[{datetime.now()}] Start parsowania (v. Categories Update)...")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        response = requests.get(URL_TO_PARSE, headers=headers)
        response.raise_for_status()
    except Exception as e:
        print(f"Błąd sieci: {e}")
        return

    # 1. Pobranie JSON
    soup = BeautifulSoup(response.text, 'lxml')
    next_data_tag = soup.find("script", id="__NEXT_DATA__")

    if not next_data_tag:
        print("CRITICAL: Nie znaleziono __NEXT_DATA__.")
        return

    try:
        full_json = json.loads(next_data_tag.text)
    except json.JSONDecodeError:
        print("Błąd dekodowania JSON.")
        return

    # 2. Nawigacja do danych
    props = full_json.get('props', {})
    app_data = props.get('app', {})

    if not app_data:
        app_data = props.get('pageProps', {}).get('app', {})

    if not app_data:
        print("Błąd: Obiekt 'app' nie znaleziony w JSON.")
        return

    raw_categories = app_data.get('categories', [])
    menu_items = app_data.get('menu', [])

    print(f"Znaleziono: {len(menu_items)} produktów w {len(raw_categories)} kategoriach.")

    # 3. Mapa Kategorii
    categories_map = {}
    for cat in raw_categories:
        cat_id = cat.get('_id')
        if cat_id:
            categories_map[cat_id] = {
                'name': cat.get('name', 'Menu'),
                'hurl': cat.get('hurl', 'other')
            }

    # 4. Generowanie XML
    rss = ET.Element("rss", {"xmlns:g": "http://base.google.com/ns/1.0", "version": "2.0"})
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = "Sushi Ulov Menu Feed"
    ET.SubElement(channel, "link").text = BASE_URL
    ET.SubElement(channel, "description").text = "Daily updated product feed"

    success_count = 0

    for item in menu_items:
        try:
            # --- DANE PRODUKTU ---

            # Nazwa
            title = item.get('name')
            if not title: continue

            # Cena (Dzielona przez 100)
            price_val = clean_price(item.get('price'))
            if float(price_val) <= 0: continue

            # ID
            p_id = item.get('_id')
            if not p_id:
                p_id = hashlib.md5(title.encode('utf-8')).hexdigest()[:12]

            # Opis
            description = item.get('description')
            if not description: description = title

            # --- KATEGORIE I LINKI ---
            cat_id = item.get('category')
            cat_data = categories_map.get(cat_id, {'name': 'Menu', 'hurl': 'menu'})

            # 1. Product Type (Wewnętrzna kategoria sklepu)
            product_type = cat_data['name']

            # 2. Google Category ID (Na podstawie Twojej tabeli)
            google_cat_id = get_google_category_id(product_type)

            # Link
            item_hurl = item.get('hurl')
            if item_hurl:
                cat_hurl = cat_data['hurl']
                link = f"{BASE_URL}/{URL_PREFIX}/{cat_hurl}/{item_hurl}"
            else:
                link = URL_TO_PARSE

            # Zdjęcie
            image_link = ""
            media = item.get('media')
            if isinstance(media, dict):
                image_link = media.get('url', "")
            elif isinstance(media, list) and media:
                image_link = media[0].get('url', "")

            if image_link and image_link.startswith('/'):
                image_link = BASE_URL + image_link

            if not image_link: continue

            # Dostępność
            is_avail = item.get('available', True)
            availability = get_availability(is_avail)

            # --- ZAPIS DO XML ---
            xml_item = ET.SubElement(channel, "item")

            # Pola Wymagane
            ET.SubElement(xml_item, "g:id").text = str(p_id)
            ET.SubElement(xml_item, "g:title").text = title
            ET.SubElement(xml_item, "g:description").text = description
            ET.SubElement(xml_item, "g:link").text = link
            ET.SubElement(xml_item, "g:image_link").text = image_link
            ET.SubElement(xml_item, "g:price").text = f"{price_val} PLN"
            ET.SubElement(xml_item, "g:availability").text = availability
            ET.SubElement(xml_item, "g:brand").text = "Sushi Ulov"
            ET.SubElement(xml_item, "g:condition").text = "new"

            # Kategorie
            ET.SubElement(xml_item, "g:google_product_category").text = google_cat_id
            ET.SubElement(xml_item, "g:product_type").text = product_type

            # Cena Promocyjna
            sale_price_raw = item.get('discountPrice')
            if sale_price_raw:
                sale_val = clean_price(sale_price_raw)
                if float(sale_val) > 0 and float(sale_val) < float(price_val):
                    ET.SubElement(xml_item, "g:sale_price").text = f"{sale_val} PLN"

            success_count += 1

        except Exception as e:
            continue

    # Zapis pliku
    tree = ET.ElementTree(rss)
    tree.write(OUTPUT_FILE, encoding='UTF-8', xml_declaration=True)
    print(f"[{datetime.now()}] Wygenerowano {success_count} produktów.")
    print(f"Plik: {OUTPUT_FILE}")


if __name__ == "__main__":
    if not os.path.exists("/data"):
        run_parser()
    else:
        while True:
            run_parser()
            time.sleep(3600) # skrypt aktualizuje dane co godzinę