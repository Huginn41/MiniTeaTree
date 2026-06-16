"""Парсер YML/YML-фидов ( Яндекс.Маркет формат).

Поддерживает URL или локальный файл. Извлекает категории, товары, варианты
(граммовки) и ссылки на картинки. Скачивание фото — отдельный сервис (image.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from lxml import etree

from app.logging import get_logger

log = get_logger("services.yml_parser")


@dataclass
class ParsedCategory:
    """Категория из YML."""

    id: str  # YML category id (строка)
    name: str
    parent_id: str | None = None


@dataclass
class ParsedVariant:
    """Вариант товара (граммовка/цена) из YML offer-params."""

    weight_g: int
    price: float
    sku: str | None = None


@dataclass
class ParsedOffer:
    """Товар (offer) из YML."""

    id: str
    name: str
    category_id: str
    description: str = ""
    price: float = 0.0
    picture_urls: list[str] = field(default_factory=list)
    params: dict[str, str] = field(default_factory=dict)
    vendor: str = ""
    # Ищем параметр «вес» для автоматического создания вариантов.
    weight_param: str | None = None


@dataclass
class ParsedFeed:
    """Результат парсинга YML-фида."""

    shop_name: str = ""
    categories: list[ParsedCategory] = field(default_factory=list)
    offers: list[ParsedOffer] = field(default_factory=list)


def _parse_categories(categories_el) -> list[ParsedCategory]:
    """Разбирает <categories>."""
    result = []
    for cat in categories_el.findall("category"):
        cat_id = cat.get("id", "")
        parent_id = cat.get("parentId")
        name = (cat.text or "").strip()
        if cat_id and name:
            result.append(
                ParsedCategory(id=cat_id, name=name, parent_id=parent_id)
            )
    return result


def _parse_offers(offers_el) -> list[ParsedOffer]:
    """Разбирает <offers>."""
    result = []
    for offer in offers_el.findall("offer"):
        offer_id = offer.get("id", "")
        name_el = offer.find("name")
        if name_el is None or not name_el.text:
            name_el = offer.find("title")
        if name_el is None or not name_el.text:
            name_el = offer.find("model")
        name = (name_el.text or "").strip() if name_el is not None else ""

        cat_el = offer.find("categoryId")
        category_id = (cat_el.text or "").strip() if cat_el is not None else ""

        price_el = offer.find("price")
        price = float(price_el.text or "0") if price_el is not None else 0.0

        desc_el = offer.find("description")
        description = (desc_el.text or "").strip() if desc_el is not None else ""

        vendor_el = offer.find("vendor")
        vendor = (vendor_el.text or "").strip() if vendor_el is not None else ""

        picture_urls: list[str] = []
        for pic_el in offer.findall("picture"):
            url = (pic_el.text or "").strip()
            if url:
                picture_urls.append(url)

        params: dict[str, str] = {}
        weight_param = None
        for param_el in offer.findall("param"):
            pname = param_el.get("name", "").strip()
            pvalue = (param_el.text or "").strip()
            if pname:
                params[pname] = pvalue
                # Ищем вес (в граммах).
                low = pname.lower()
                if "вес" in low or "масса" in low:
                    weight_param = pvalue

        result.append(
            ParsedOffer(
                id=offer_id,
                name=name,
                category_id=category_id,
                description=description,
                price=price,
                picture_urls=picture_urls,
                params=params,
                vendor=vendor,
                weight_param=weight_param,
            )
        )
    return result


def parse_yml_feed(xml_content: str | bytes) -> ParsedFeed:
    """Парсит YML-фид из строки/байтов.

    Returns ParsedFeed с категориями и офферами.
    """
    root = etree.fromstring(xml_content)
    shop = root.find("shop")
    shop_name = ""
    categories_el = None
    offers_el = None

    if shop is not None:
        name_el = shop.find("name")
        shop_name = (name_el.text or "").strip() if name_el is not None else ""
        categories_el = shop.find("categories")
        offers_el = shop.find("offers")
    else:
        # Фид без <shop> — ищем на уровне корня.
        categories_el = root.find("categories")
        offers_el = root.find("offers")

    categories = _parse_categories(categories_el) if categories_el is not None else []
    offers = _parse_offers(offers_el) if offers_el is not None else []

    log.info(
        "yml_parsed",
        shop_name=shop_name,
        categories=len(categories),
        offers=len(offers),
    )

    return ParsedFeed(shop_name=shop_name, categories=categories, offers=offers)


async def parse_yml_from_url(url: str) -> ParsedFeed:
    """Скачивает YML-фид по URL и парсит его."""
    import httpx

    log.info("yml_download_start", url=url)
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
    log.info("yml_download_done", url=url, size=len(resp.content))
    return parse_yml_feed(resp.content)
