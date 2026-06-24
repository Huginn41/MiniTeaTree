"""Клиент T Bank Acquiring API v2.

Документация: https://developer.tbank.ru/eacq/scenarios/payments/

Алгоритм подписи (Token):
  1. Берём все поля запроса (кроме Token, Receipt, DATA, Shops).
  2. Добавляем поле Password = секретный ключ терминала.
  3. Сортируем ключи по алфавиту.
  4. Конкатенируем значения (без разделителей).
  5. SHA-256 → hex.
"""

from __future__ import annotations

import hashlib
from typing import Any

import httpx

from app.config import get_settings
from app.logging import get_logger

log = get_logger("app.tbank")

_BASE_URL = "https://securepay.tinkoff.ru/v2"

# Поля, исключаемые из расчёта токена
_TOKEN_EXCLUDE = {"Token", "Receipt", "DATA", "Shops"}


def _make_token(params: dict[str, Any], password: str) -> str:
    """Вычисляет подпись запроса по алгоритму T Bank."""
    data = {k: v for k, v in params.items() if k not in _TOKEN_EXCLUDE}
    data["Password"] = password
    concat = "".join(str(data[k]) for k in sorted(data))
    return hashlib.sha256(concat.encode()).hexdigest()


def _verify_token(params: dict[str, Any], password: str) -> bool:
    """Проверяет токен входящего webhook-уведомления."""
    received = params.get("Token", "")
    expected = _make_token({k: v for k, v in params.items() if k != "Token"}, password)
    return received == expected


async def _call(method: str, payload: dict[str, Any]) -> dict[str, Any]:
    """POST к T Bank API. Возвращает JSON-ответ."""
    s = get_settings()
    terminal_key = s.tbank_terminal_key
    secret_key = s.tbank_secret_key.get_secret_value()

    if not terminal_key or not secret_key:
        log.warning("tbank_not_configured")
        return {"Success": False, "ErrorCode": "NOT_CONFIGURED"}

    payload["TerminalKey"] = terminal_key
    payload["Token"] = _make_token(payload, secret_key)

    url = f"{_BASE_URL}/{method}"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload)
        data = resp.json()
        if not data.get("Success"):
            log.warning("tbank_api_error", method=method, error=data.get("Message"), code=data.get("ErrorCode"))
        return data
    except Exception as exc:
        log.error("tbank_request_failed", method=method, error=str(exc))
        return {"Success": False, "ErrorCode": "REQUEST_FAILED"}


async def init_payment(
    *,
    order_id: int,
    order_number: str,
    amount_rub: float,
    description: str,
    customer_email: str | None = None,
    customer_phone: str | None = None,
) -> dict[str, Any]:
    """Создаёт платёж в T Bank. Возвращает полный ответ API.

    При успехе в ответе будут:
      - PaymentId: str
      - PaymentURL: str  ← отправляем клиенту
    """
    s = get_settings()
    # Сумма в копейках (целое)
    amount_kopecks = int(round(amount_rub * 100))

    payload: dict[str, Any] = {
        "Amount": amount_kopecks,
        "OrderId": str(order_number),
        "Description": description[:250],
        "NotificationURL": f"{s.public_base_url.rstrip('/')}/api/payments/tbank/webhook",
        "SuccessURL": f"{s.public_base_url.rstrip('/')}/api/payments/tbank/success",
        "FailURL": f"{s.public_base_url.rstrip('/')}/api/payments/tbank/fail",
    }

    if customer_email:
        payload["Receipt"] = {
            "Email": customer_email,
            "Taxation": "usn_income",
            "Items": [
                {
                    "Name": description[:64],
                    "Price": amount_kopecks,
                    "Quantity": 1,
                    "Amount": amount_kopecks,
                    "Tax": "none",
                }
            ],
        }

    return await _call("Init", payload)


async def cancel_payment(payment_id: str) -> dict[str, Any]:
    """Отменяет платёж (возврат до подтверждения)."""
    return await _call("Cancel", {"PaymentId": payment_id})


def is_configured() -> bool:
    """True если TerminalKey и SecretKey заданы."""
    s = get_settings()
    return bool(s.tbank_terminal_key and s.tbank_secret_key.get_secret_value())
