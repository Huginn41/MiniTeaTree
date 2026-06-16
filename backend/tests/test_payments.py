"""Тесты платежей: создание инвойса и обработка Telegram webhook."""

from __future__ import annotations

import json
import os

import pytest
import respx
from httpx import AsyncClient, Response

from app.models.cart import Cart, CartItem
from app.models.category import Category
from app.models.order import Order
from app.models.payment import PaymentEvent
from app.models.product import Product, ProductVariant
from app.models.user import User
from app.security import create_token_pair

pytestmark = pytest.mark.asyncio

# Фейковый суффикс токена (8 символов конца BOT_TOKEN из conftest: "0:fake")
_TOKEN_SUFFIX = "0:fake"[-8:]  # → "00:fake" ... берём хвост
# BOT_TOKEN в тестах = "0:fake" → суффикс для URL = "0:fake" целиком (короткий)
_WEBHOOK_PATH = f"/api/payments/webhook/telegram/0:fake"


def _auth(user: User) -> dict:
    access, _ = create_token_pair(user.telegram_id)
    return {"Authorization": f"Bearer {access}"}


@pytest.fixture
async def order_data(db_session):
    """Пользователь с готовым заказом в статусе pending."""
    user = User(telegram_id=55566677, first_name="Pay")
    db_session.add(user)
    await db_session.flush()

    cat = Category(name="Чай", slug="tea-pay", sort_order=0)
    db_session.add(cat)
    await db_session.flush()

    product = Product(category_id=cat.id, name="Сенча Pay", slug="sencha-pay", base_price=500, sort_order=0)
    db_session.add(product)
    await db_session.flush()

    variant = ProductVariant(product_id=product.id, weight_g=50, price=500, in_stock=True)
    db_session.add(variant)
    await db_session.flush()

    order = Order(
        user_id=user.id,
        number="ЧД-000099",
        total_amount=1000,
        status_payment="pending",
        status_delivery="new",
    )
    db_session.add(order)
    await db_session.commit()

    return {"user": user, "order": order, "variant": variant}


# ---------- create invoice ----------

@respx.mock
async def test_create_invoice_ok(client: AsyncClient, order_data):
    """Успешное создание invoice link через Telegram Bot API."""
    user = order_data["user"]
    order = order_data["order"]

    # Мокаем вызов Telegram API
    respx.post("https://api.telegram.org/bot0:fake/createInvoiceLink").mock(
        return_value=Response(200, json={"ok": True, "result": "slug_abc123"})
    )

    resp = await client.post(
        f"/api/payments/{order.number}/invoice",
        headers=_auth(user),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["order_number"] == order.number
    assert "t.me" in data["invoice_url"]


@respx.mock
async def test_create_invoice_already_paid(client: AsyncClient, order_data, db_session):
    """Создание инвойса для уже оплаченного заказа → 400."""
    user = order_data["user"]
    order = order_data["order"]
    order.status_payment = "paid"
    await db_session.commit()

    resp = await client.post(
        f"/api/payments/{order.number}/invoice",
        headers=_auth(user),
    )
    assert resp.status_code == 400
    assert "pending" in resp.json()["detail"]


async def test_create_invoice_not_found(client: AsyncClient, order_data, db_session):
    """Чужой пользователь пытается оплатить чужой заказ → 404."""
    # Создаём другого пользователя в БД (иначе JWT-валидация вернёт 401)
    other = User(telegram_id=99988877, first_name="Other")
    db_session.add(other)
    await db_session.commit()

    resp = await client.post(
        "/api/payments/ЧД-000099/invoice",
        headers=_auth(other),
    )
    assert resp.status_code == 404


async def test_create_invoice_no_provider_token(client: AsyncClient, order_data, monkeypatch):
    """Нет YOOKASSA_PROVIDER_TOKEN → 503."""
    from app.config import get_settings
    settings = get_settings()
    monkeypatch.setattr(
        settings.yookassa_provider_token,
        "get_secret_value",
        lambda: "",
    )

    resp = await client.post(
        f"/api/payments/{order_data['order'].number}/invoice",
        headers=_auth(order_data["user"]),
    )
    assert resp.status_code == 503


async def test_create_invoice_unauthorized(client: AsyncClient):
    resp = await client.post("/api/payments/ЧД-000001/invoice")
    assert resp.status_code == 401


# ---------- webhook pre_checkout ----------

async def test_webhook_pre_checkout_ok(client: AsyncClient, order_data, db_session):
    """pre_checkout_query с корректной суммой → answerPreCheckoutQuery(ok=True)."""
    order = order_data["order"]

    with respx.mock:
        respx.post("https://api.telegram.org/bot0:fake/answerPreCheckoutQuery").mock(
            return_value=Response(200, json={"ok": True, "result": True})
        )

        update = {
            "pre_checkout_query": {
                "id": "pq_111",
                "from": {"id": 55566677},
                "currency": "RUB",
                "total_amount": 100000,  # 1000 руб × 100 копеек
                "invoice_payload": order.number,
            }
        }
        resp = await client.post(_WEBHOOK_PATH, json=update)
        assert resp.status_code == 200
        assert resp.json()["ok"] is True


async def test_webhook_pre_checkout_wrong_amount(client: AsyncClient, order_data):
    """pre_checkout_query с неверной суммой → answerPreCheckoutQuery(ok=False)."""
    order = order_data["order"]

    with respx.mock:
        mock_answer = respx.post(
            "https://api.telegram.org/bot0:fake/answerPreCheckoutQuery"
        ).mock(return_value=Response(200, json={"ok": True, "result": True}))

        update = {
            "pre_checkout_query": {
                "id": "pq_222",
                "from": {"id": 55566677},
                "currency": "RUB",
                "total_amount": 1,  # неправильная сумма
                "invoice_payload": order.number,
            }
        }
        resp = await client.post(_WEBHOOK_PATH, json=update)
        assert resp.status_code == 200
        # Убедимся, что отправили ok=False
        call = mock_answer.calls[0]
        body = json.loads(call.request.content)
        assert body["ok"] is False


async def test_webhook_pre_checkout_unknown_order(client: AsyncClient):
    """pre_checkout_query для несуществующего заказа → ok=False."""
    with respx.mock:
        mock_answer = respx.post(
            "https://api.telegram.org/bot0:fake/answerPreCheckoutQuery"
        ).mock(return_value=Response(200, json={"ok": True, "result": True}))

        update = {
            "pre_checkout_query": {
                "id": "pq_333",
                "from": {"id": 1},
                "currency": "RUB",
                "total_amount": 50000,
                "invoice_payload": "ЧД-999999",
            }
        }
        resp = await client.post(_WEBHOOK_PATH, json=update)
        assert resp.status_code == 200
        call = mock_answer.calls[0]
        body = json.loads(call.request.content)
        assert body["ok"] is False


# ---------- webhook successful_payment ----------

async def test_webhook_successful_payment(client: AsyncClient, order_data, db_session):
    """successful_payment → order.status_payment = paid + PaymentEvent создан."""
    order = order_data["order"]

    update = {
        "message": {
            "from": {"id": 55566677},
            "successful_payment": {
                "currency": "RUB",
                "total_amount": 100000,
                "invoice_payload": order.number,
                "telegram_payment_charge_id": "tg_charge_001",
                "provider_payment_charge_id": "yoo_charge_001",
            },
        }
    }
    resp = await client.post(_WEBHOOK_PATH, json=update)
    assert resp.status_code == 200

    await db_session.refresh(order)
    assert order.status_payment == "paid"
    assert order.paid_at is not None

    from sqlalchemy import select
    events = (await db_session.execute(
        select(PaymentEvent).where(PaymentEvent.order_id == order.id)
    )).scalars().all()
    assert len(events) == 1
    assert events[0].status == "paid"
    assert events[0].external_id == "yoo_charge_001"


async def test_webhook_successful_payment_idempotent(client: AsyncClient, order_data, db_session):
    """Повторный successful_payment не создаёт дубль PaymentEvent."""
    order = order_data["order"]
    order.status_payment = "paid"
    await db_session.commit()

    update = {
        "message": {
            "from": {"id": 55566677},
            "successful_payment": {
                "currency": "RUB",
                "total_amount": 100000,
                "invoice_payload": order.number,
                "telegram_payment_charge_id": "tg_charge_002",
                "provider_payment_charge_id": "yoo_charge_002",
            },
        }
    }
    resp = await client.post(_WEBHOOK_PATH, json=update)
    assert resp.status_code == 200

    from sqlalchemy import select
    events = (await db_session.execute(
        select(PaymentEvent).where(PaymentEvent.order_id == order.id)
    )).scalars().all()
    # Новое событие НЕ добавляется (заказ уже paid)
    assert len(events) == 0


async def test_webhook_invalid_token_suffix(client: AsyncClient):
    """Запрос с неверным суффиксом токена → 403."""
    resp = await client.post("/api/payments/webhook/telegram/wrongtoken", json={})
    assert resp.status_code == 403


async def test_webhook_unknown_update(client: AsyncClient):
    """Неизвестный тип update → 200 (просто игнорируем)."""
    resp = await client.post(_WEBHOOK_PATH, json={"edited_message": {}})
    assert resp.status_code == 200
