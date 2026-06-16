"""Тесты YML-парсера."""

from __future__ import annotations

from app.services.yml_parser import parse_yml_feed

SAMPLE_YML = """<yml_catalog date="2025-01-01 12:00">
  <shop>
    <name>Чайное Дерево</name>
    <company>ООО Чайное Дерево</company>
    <url>https://example.com</url>
    <categories>
      <category id="1">Зелёный чай</category>
      <category id="2">Чёрный чай</category>
    </categories>
    <offers>
      <offer id="101">
        <name>Сенча премиум</name>
        <categoryId>1</categoryId>
        <price>1200</price>
        <currencyId>RUR</currencyId>
        <picture>https://example.com/img/sencha1.jpg</picture>
        <picture>https://example.com/img/sencha2.jpg</picture>
        <description>Японский зелёный чай высшего качества</description>
        <vendor>Чайное Дерево</vendor>
        <param name="Вес">50</param>
      </offer>
      <offer id="102">
        <name>Эрл Грей</name>
        <categoryId>2</categoryId>
        <price>800</price>
        <currencyId>RUR</currencyId>
        <picture>https://example.com/img/earl-grey.jpg</picture>
        <description>Классический чёрный чай с бергамотом</description>
        <param name="Масса нетто">100</param>
      </offer>
    </offers>
  </shop>
</yml_catalog>
"""


def test_parse_yml_categories():
    feed = parse_yml_feed(SAMPLE_YML)
    assert feed.shop_name == "Чайное Дерево"
    assert len(feed.categories) == 2
    assert feed.categories[0].id == "1"
    assert feed.categories[0].name == "Зелёный чай"


def test_parse_yml_offers():
    feed = parse_yml_feed(SAMPLE_YML)
    assert len(feed.offers) == 2

    o1 = feed.offers[0]
    assert o1.id == "101"
    assert o1.name == "Сенча премиум"
    assert o1.category_id == "1"
    assert o1.price == 1200.0
    assert len(o1.picture_urls) == 2
    assert o1.description == "Японский зелёный чай высшего качества"
    assert o1.vendor == "Чайное Дерево"
    assert o1.weight_param == "50"
    assert o1.params["Вес"] == "50"


def test_parse_yml_offer_weight_param_variants():
    o2 = parse_yml_feed(SAMPLE_YML).offers[1]
    assert o2.weight_param == "100"
    # "Масса нетто" тоже должен распознаться как вес.
    assert o2.params["Масса нетто"] == "100"


def test_parse_yml_empty():
    feed = parse_yml_feed("<yml_catalog><shop><name/></shop></yml_catalog>")
    assert feed.shop_name == ""
    assert len(feed.categories) == 0
    assert len(feed.offers) == 0
