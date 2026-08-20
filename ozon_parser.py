import json
import re
from urllib.parse import quote

import requests


OZON_API = "https://www.ozon.ru/api/entrypoint-api.bx/page/json/v2"


def parse_price(value):
    """Превращает цену вида '1 299 ₽' или '1299' в число."""
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    value = str(value)
    value = value.replace("\xa0", " ")
    value = value.replace("₽", "")
    value = value.replace("руб.", "")
    value = value.replace(" ", "")
    value = value.replace(",", ".")

    match = re.search(r"\d+(?:\.\d+)?", value)

    if not match:
        return None

    return float(match.group())


def find_values(data, result=None):
    """Рекурсивно ищет словари с информацией о товарах."""
    if result is None:
        result = []

    if isinstance(data, dict):
        keys = set(data.keys())

        # Возможная карточка товара
        if (
            ("title" in keys or "name" in keys)
            and ("price" in keys or "finalPrice" in keys or "priceInfo" in keys)
        ):
            result.append(data)

        for value in data.values():
            find_values(value, result)

    elif isinstance(data, list):
        for item in data:
            find_values(item, result)

    return result


def extract_product(card):
    """Пытается достать основные данные товара."""

    title = card.get("title") or card.get("name")

    # Цена
    price = (
        card.get("finalPrice")
        or card.get("price")
        or card.get("priceValue")
    )

    if isinstance(price, dict):
        price = (
            price.get("value")
            or price.get("price")
            or price.get("final")
        )

    if price is None:
        price_info = card.get("priceInfo")

        if isinstance(price_info, dict):
            price = (
                price_info.get("finalPrice")
                or price_info.get("price")
                or price_info.get("value")
            )

    price = parse_price(price)

    # Ссылка
    url = card.get("url") or card.get("link")

    if not url:
        product_id = (
            card.get("id")
            or card.get("productId")
            or card.get("sku")
        )

        if product_id:
            url = f"https://www.ozon.ru/product/{product_id}/"

    if url and url.startswith("/"):
        url = "https://www.ozon.ru" + url

    # Изображение
    image = (
        card.get("image")
        or card.get("imageUrl")
        or card.get("picture")
    )

    if isinstance(image, dict):
        image = (
            image.get("url")
            or image.get("src")
        )

    if isinstance(image, list) and image:
        image = image[0]

    if isinstance(image, dict):
        image = image.get("url") or image.get("src")

    return {
        "title": title,
        "price": price,
        "url": url,
        "image": image,
    }


def search_ozon(query, limit=50):
    """
    Ищет товары Ozon по запросу.
    Возвращает список товаров.
    """

    search_url = f"/search/?text={quote(query)}"

    params = {
        "url": search_url
    }

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 15) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/138.0.0.0 Mobile Safari/537.36"
        ),
        "Accept": "application/json,text/plain,*/*",
        "Accept-Language": "ru-RU,ru;q=0.9",
        "Referer": "https://www.ozon.ru/",
    }

    response = requests.get(
        OZON_API,
        params=params,
        headers=headers,
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    cards = find_values(data)

    products = []
    seen = set()

    for card in cards:
        product = extract_product(card)

        title = product["title"]
        price = product["price"]
        url = product["url"]

        if not title or price is None or not url:
            continue

        key = url

        if key in seen:
            continue

        seen.add(key)

        products.append(product)

        if len(products) >= limit:
            break

    products.sort(key=lambda item: item["price"])

    return products


def search_cheapest(query, count=5):
    """Возвращает самые дешёвые товары."""

    products = search_ozon(query, limit=50)

    return products[:count]


if __name__ == "__main__":
    result = search_cheapest("кофе 1 кг")

    print(json.dumps(
        result,
        ensure_ascii=False,
        indent=2
    ))
