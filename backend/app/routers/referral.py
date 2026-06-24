"""Роутер реферальной программы."""

from __future__ import annotations

import secrets
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_db
from app.deps import CurrentUser, get_current_user
from app.logging import get_logger
from app.models.bonus import BonusTransaction
from app.models.referral import ReferralLink
from app.models.user import User
from app.schemas import ReferralClaimResult, ReferralInfo

log = get_logger("app.referral")

router = APIRouter(prefix="/referral", tags=["referral"])


def _make_referral_link(code: str, settings) -> str:
    """Формирует ссылку для шаринга через бота."""
    bot_username = settings.telegram_channel_id  # используем отдельное поле если будет
    # Ссылка формата t.me/BotName?start=REF_code — бот передаёт code в URL мини-апп
    return f"https://t.me/teatree96_bot?start=REF_{code}"


async def _check_channel_subscription(telegram_id: int) -> bool:
    """Проверяет подписку пользователя на канал через Telegram Bot API."""
    from aiogram import Bot
    settings = get_settings()
    channel_id = settings.telegram_channel_id
    if not channel_id:
        log.warning("telegram_channel_id_not_configured")
        return False

    token = settings.bot_token.get_secret_value()
    if not token or token.startswith("0:"):
        # dev-режим без реального бота
        return False

    try:
        from aiogram.client.session.aiohttp import AiohttpSession
        from aiogram.client.telegram import TelegramAPIServer

        session_kwargs = {}
        if settings.telegram_api_base_url:
            api_server = TelegramAPIServer.from_base(settings.telegram_api_base_url)
            session_kwargs["session"] = AiohttpSession(api=api_server)

        bot = Bot(token=token, **session_kwargs)
        member = await bot.get_chat_member(chat_id=channel_id, user_id=telegram_id)
        await bot.session.close()
        return member.status not in ("left", "kicked", "banned")
    except Exception as exc:
        log.warning("channel_check_failed", error=str(exc), telegram_id=telegram_id)
        return False


@router.get("/info", response_model=ReferralInfo)
async def get_referral_info(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ReferralInfo:
    """Возвращает реферальную информацию текущего пользователя."""
    u = user.user
    settings = get_settings()

    referral_link = None
    if u.referral_code:
        referral_link = _make_referral_link(u.referral_code, settings)

    # Считаем кол-во реципиентов
    count_r = await session.execute(
        select(func.count()).select_from(ReferralLink).where(ReferralLink.donor_id == u.id)
    )
    recipients_count = count_r.scalar() or 0

    return ReferralInfo(
        is_channel_member=u.is_channel_member,
        referral_code=u.referral_code,
        referral_link=referral_link,
        slots_total=u.referral_slots,
        slots_used=u.referral_slots_used,
        recipients_count=recipients_count,
    )


@router.post("/register")
async def register_referrer(
    ref_code: str,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Записывает донора для текущего пользователя при открытии по реферальной ссылке.

    Вызывается фронтендом при старте, если в URL есть ?ref=REF_xxx.
    Работает только если:
    - пользователь ещё не привязан к донору
    - пользователь ещё не является участником (не подписан)
    - код реферала валиден и принадлежит существующему пользователю с активными слотами
    """
    u = user.user

    # Уже привязан к донору — ничего не делаем
    if u.referrer_id is not None:
        return {"ok": True, "message": "already_registered"}

    # Уже участник — ничего не делаем
    if u.is_channel_member:
        return {"ok": True, "message": "already_member"}

    # Убираем префикс REF_ если есть
    code = ref_code.removeprefix("REF_")

    # Ищем донора по коду
    donor_r = await session.execute(
        select(User).where(User.referral_code == code)
    )
    donor = donor_r.scalar_one_or_none()
    if donor is None:
        return {"ok": False, "message": "invalid_code"}

    # Нельзя пригласить самого себя
    if donor.id == u.id:
        return {"ok": False, "message": "self_referral"}

    # Привязываем реципиента к донору даже если слотов нет сейчас —
    # слоты могут появиться после первой покупки донора.
    # Бонус выдаётся в /claim только если у донора есть свободные слоты.

    # Блокируем строку пользователя
    u_locked = await session.execute(
        select(User).where(User.id == u.id).with_for_update()
    )
    u = u_locked.scalar_one()
    u.referrer_id = donor.id
    session.add(u)
    await session.commit()

    return {"ok": True, "message": "registered"}


@router.post("/claim", response_model=ReferralClaimResult)
async def claim_referral_bonus(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ReferralClaimResult:
    """Пользователь нажал «Я подписался» — проверяем подписку и начисляем бонус.

    Логика:
    1. Проверяем подписку через Telegram API
    2. Помечаем is_channel_member = True
    3. Генерируем referral_code (становится донором)
    4. Если у пользователя есть донор И у донора есть свободный слот — начисляем 250 баллов
    5. Обновляем счётчик слотов у донора
    """
    settings = get_settings()
    welcome_bonus = settings.referral_welcome_bonus

    # Блокируем строку пользователя
    u_r = await session.execute(
        select(User).where(User.id == user.user.id).with_for_update()
    )
    u = u_r.scalar_one()

    # Уже участник
    if u.is_channel_member:
        return ReferralClaimResult(success=True, message="already_member", bonus_awarded=0)

    # Проверяем подписку
    is_subscribed = await _check_channel_subscription(u.telegram_id)
    if not is_subscribed:
        return ReferralClaimResult(success=False, message="not_subscribed", bonus_awarded=0)

    # Помечаем участником и генерируем реферальный код
    u.is_channel_member = True
    if not u.referral_code:
        u.referral_code = secrets.token_hex(4).upper()  # 8 символов

    bonus_awarded = 0

    # Начисляем велком-бонус если пришёл по ссылке донора и у донора есть слоты
    if u.referrer_id:
        # Проверяем не был ли уже создан ReferralLink (дублирование)
        existing_r = await session.execute(
            select(ReferralLink).where(ReferralLink.recipient_id == u.id)
        )
        existing = existing_r.scalar_one_or_none()

        if existing is None:
            donor_r = await session.execute(
                select(User).where(User.id == u.referrer_id).with_for_update()
            )
            donor = donor_r.scalar_one_or_none()

            if donor and donor.referral_slots_used < donor.referral_slots:
                # Создаём связь донор→реципиент
                ref_link = ReferralLink(
                    donor_id=donor.id,
                    recipient_id=u.id,
                    welcome_paid=True,
                    purchases_rewarded=0,
                )
                session.add(ref_link)

                # Начисляем велком-бонус реципиенту
                u.bonus_balance = Decimal(str(float(u.bonus_balance) + welcome_bonus))
                session.add(BonusTransaction(
                    user_id=u.id,
                    delta=Decimal(str(welcome_bonus)),
                    reason="referral_welcome",
                    note=f"Велком-бонус за вступление по ссылке донора #{donor.id}",
                ))

                # Увеличиваем счётчик использованных слотов у донора
                donor.referral_slots_used += 1
                session.add(donor)

                bonus_awarded = welcome_bonus

    session.add(u)
    await session.commit()

    return ReferralClaimResult(
        success=True,
        message="subscribed",
        bonus_awarded=bonus_awarded,
    )
