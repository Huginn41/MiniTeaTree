"""Роуты /admin-api/* и кастомные HTML-страницы /admin/*."""

from __future__ import annotations

import uuid as _uuid
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse as _JSONResponse, HTMLResponse as _HTMLResponse
from starlette.requests import Request

from app.admin.upload import (
    UPLOADS_DIR as _UPLOADS_DIR,
    UPLOAD_MAX_BYTES as _UPLOAD_MAX_BYTES,
    to_webp as _to_webp,
    delete_upload_file as _delete_upload_file,
)

router = APIRouter()

@router.post("/admin-api/upload")
async def admin_upload(request: Request):
    if request.session.get("admin_token") != "authenticated":
        return _JSONResponse(status_code=401, content={"error": "Unauthorized"})
    try:
        form = await request.form(max_part_size=_UPLOAD_MAX_BYTES)
    except Exception:
        return _JSONResponse(status_code=413, content={"error": "Файл слишком большой (макс. 15 МБ)"})
    file = form.get("file")
    if file is None:
        return _JSONResponse(status_code=400, content={"error": "Нет файла"})
    _UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    name = f"{_uuid.uuid4().hex}.webp"
    try:
        _to_webp(await file.read(), _UPLOADS_DIR / name)
    except ValueError as exc:
        return _JSONResponse(status_code=422, content={"error": str(exc)})
    except Exception as exc:
        import logging as _log
        _log.getLogger(__name__).exception("Upload error: %s", exc)
        return _JSONResponse(status_code=500, content={"error": "Ошибка обработки изображения"})
    return _JSONResponse({"path": f"/static/media/uploads/{name}"})

@router.get("/admin-api/product/{product_id}/images")
async def admin_product_images(product_id: int, request: Request):
    if request.session.get("admin_token") != "authenticated":
        return _JSONResponse(status_code=401, content={"error": "Unauthorized"})
    from app.db import get_session_factory
    from app.models.product import ProductImage
    from sqlalchemy import select
    async with get_session_factory()() as session:
        res = await session.execute(
            select(ProductImage).where(ProductImage.product_id == product_id).order_by(ProductImage.sort)
        )
        imgs = res.scalars().all()
        return _JSONResponse([{"id": i.id, "path": i.path, "is_main": i.is_main, "alt": i.alt or "", "sort": i.sort} for i in imgs])

@router.post("/admin-api/product/{product_id}/images")
async def admin_product_image_upload(product_id: int, request: Request):
    if request.session.get("admin_token") != "authenticated":
        return _JSONResponse(status_code=401, content={"error": "Unauthorized"})
    try:
        form = await request.form(max_part_size=_UPLOAD_MAX_BYTES)
    except Exception:
        return _JSONResponse(status_code=413, content={"error": "Файл слишком большой (макс. 15 МБ)"})
    file = form.get("file")
    if file is None:
        return _JSONResponse(status_code=400, content={"error": "Нет файла"})
    _UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    name = f"{_uuid.uuid4().hex}.webp"
    try:
        _to_webp(await file.read(), _UPLOADS_DIR / name)
    except Exception as exc:
        import logging as _log
        _log.getLogger(__name__).exception("Product image upload error: %s", exc)
        return _JSONResponse(status_code=422, content={"error": "Ошибка обработки изображения"})
    path = f"/static/media/uploads/{name}"
    from app.db import get_session_factory
    from app.models.product import ProductImage
    from sqlalchemy import select, func
    async with get_session_factory()() as session:
        count_res = await session.execute(
            select(func.count()).where(ProductImage.product_id == product_id)
        )
        count = count_res.scalar() or 0
        img = ProductImage(product_id=product_id, path=path, is_main=(count == 0), sort=count)
        session.add(img)
        await session.commit()
        await session.refresh(img)
        return _JSONResponse({"id": img.id, "path": img.path, "is_main": img.is_main})

@router.delete("/admin-api/product-image/{image_id}")
async def admin_delete_product_image(image_id: int, request: Request):
    if request.session.get("admin_token") != "authenticated":
        return _JSONResponse(status_code=401, content={"error": "Unauthorized"})
    from app.db import get_session_factory
    from app.models.product import ProductImage
    from sqlalchemy import select
    async with get_session_factory()() as session:
        res = await session.execute(select(ProductImage).where(ProductImage.id == image_id))
        img = res.scalar_one_or_none()
        if img:
            _delete_upload_file(img.path)
            await session.delete(img)
            await session.commit()
    return _JSONResponse({"ok": True})

@router.post("/admin-api/product-image/{image_id}/set-main")
async def admin_set_main_image(image_id: int, request: Request):
    if request.session.get("admin_token") != "authenticated":
        return _JSONResponse(status_code=401, content={"error": "Unauthorized"})
    from app.db import get_session_factory
    from app.models.product import ProductImage
    from sqlalchemy import select
    async with get_session_factory()() as session:
        res = await session.execute(select(ProductImage).where(ProductImage.id == image_id))
        img = res.scalar_one_or_none()
        if not img:
            return _JSONResponse(status_code=404, content={"error": "Not found"})
        all_res = await session.execute(
            select(ProductImage).where(ProductImage.product_id == img.product_id)
        )
        for i in all_res.scalars().all():
            i.is_main = (i.id == image_id)
        await session.commit()
    return _JSONResponse({"ok": True})

@router.post("/admin-api/order/{order_id}/status")
async def admin_update_order_status(order_id: int, request: Request):
    if request.session.get("admin_token") != "authenticated":
        return _JSONResponse(status_code=401, content={"error": "Unauthorized"})
    data = await request.json()
    field = data.get("field")
    value = data.get("value")
    if field != "status":
        return _JSONResponse(status_code=400, content={"error": "Invalid field"})
    from app.models.enums import ORDER_STATUS_VALUES
    if value not in ORDER_STATUS_VALUES:
        return _JSONResponse(status_code=400, content={"error": "Invalid status value"})
    from datetime import UTC, datetime as _dt
    from app.db import get_session_factory
    from sqlalchemy.orm import selectinload as _sil
    user_telegram_id = None
    async with get_session_factory()() as session:
        result = await session.execute(
            select(Order).options(_sil(Order.user)).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        if not order:
            return _JSONResponse(status_code=404, content={"error": "Not found"})
        old_status = order.status
        order.status = value
        if value == "delivered" and not order.delivered_at:
            order.delivered_at = _dt.now(UTC)
        if value == "in_delivery" and not order.paid_at:
            order.paid_at = _dt.now(UTC)
        if order.user:
            user_telegram_id = order.user.telegram_id
        order_number = order.number
        await session.commit()
    # Уведомляем клиента и обновляем карточки у менеджеров
    if old_status != value:
        try:
            import asyncio as _aio
            if user_telegram_id:
                from app.bot.status_notify import notify_status_changed as _notify
                _aio.create_task(_notify(
                    Order(id=order_id, number=order_number, status=value),
                    value,
                    user_telegram_id,
                ))
            from app.bot.notify import update_order_notifications as _upd
            _aio.create_task(_upd(order_id))
        except Exception:
            pass
    return _JSONResponse({"ok": True})

# ===== CRM ЗАКАЗА =====

@router.get("/crm/order/{order_id}", include_in_schema=False)
async def admin_crm_order(order_id: int, request: Request):
    if request.session.get("admin_token") != "authenticated":
        from starlette.responses import RedirectResponse
        return RedirectResponse("/admin/login")
    from app.db import get_session_factory
    from sqlalchemy.orm import selectinload
    async with get_session_factory()() as session:
        result = await session.execute(
            select(Order)
            .options(
                selectinload(Order.items),
                selectinload(Order.delivery_info),
                selectinload(Order.user),
            )
            .where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
    if not order:
        return _JSONResponse(status_code=404, content={"error": "Not found"})
    from fastapi.responses import HTMLResponse as _HTMLResponse
    from app.admin.crm_order import render_crm_order
    admin_username = request.session.get("admin_username", "")
    html = render_crm_order(order, admin_username=admin_username)
    return _HTMLResponse(html)


@router.patch("/admin-api/customer/{user_id}", include_in_schema=False)
async def admin_customer_patch(user_id: int, request: Request):
    if request.session.get("admin_token") != "authenticated":
        return _JSONResponse(status_code=401, content={"error": "Unauthorized"})
    if request.session.get("admin_readonly"):
        return _JSONResponse(status_code=403, content={"error": "Readonly"})
    data = await request.json()
    from app.db import get_session_factory
    from app.models.user import User as _User
    async with get_session_factory()() as session:
        result = await session.execute(select(_User).where(_User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return _JSONResponse(status_code=404, content={"error": "Not found"})
        if "segment" in data:
            user.segment = data["segment"] or None
        if "notes" in data:
            user.notes = data["notes"] or None
        await session.commit()
    return _JSONResponse({"ok": True})

# ── Бонусная система ────────────────────────────────────────────────────────


@router.get("/admin-api/bonus/settings", include_in_schema=False)
async def admin_bonus_settings_get(request: Request):
    if request.session.get("admin_token") != "authenticated":
        return _JSONResponse(status_code=401, content={"error": "Unauthorized"})
    from app.db import get_session_factory
    from app.models.bonus import ShopSettings as _ShopSettings
    from sqlalchemy import select as _sel
    async with get_session_factory()() as session:
        res = await session.execute(_sel(_ShopSettings).where(_ShopSettings.id == 1))
        s = res.scalar_one_or_none()
    return _JSONResponse({
        "bonus_max_payment_pct": s.bonus_max_payment_pct if s else 50,
        "bonus_no_cashback_on_redemption": bool(s.bonus_no_cashback_on_redemption) if s else False,
    })

@router.patch("/admin-api/bonus/settings", include_in_schema=False)
async def admin_bonus_settings_patch(request: Request):
    if request.session.get("admin_token") != "authenticated":
        return _JSONResponse(status_code=401, content={"error": "Unauthorized"})
    data = await request.json()
    pct = int(data.get("bonus_max_payment_pct", 50))
    pct = max(0, min(99, pct))
    no_cashback = bool(data.get("bonus_no_cashback_on_redemption", False))
    from app.db import get_session_factory
    from app.models.bonus import ShopSettings as _ShopSettings
    from sqlalchemy import select as _sel
    async with get_session_factory()() as session:
        res = await session.execute(_sel(_ShopSettings).where(_ShopSettings.id == 1))
        s = res.scalar_one_or_none()
        if s:
            s.bonus_max_payment_pct = pct
            s.bonus_no_cashback_on_redemption = no_cashback
        else:
            session.add(_ShopSettings(id=1, bonus_max_payment_pct=pct, bonus_no_cashback_on_redemption=no_cashback))
        await session.commit()
    return _JSONResponse({"ok": True, "bonus_max_payment_pct": pct, "bonus_no_cashback_on_redemption": no_cashback})

@router.put("/admin-api/bonus/tiers", include_in_schema=False)
async def admin_bonus_tiers_put(request: Request):
    if request.session.get("admin_token") != "authenticated":
        return _JSONResponse(status_code=401, content={"error": "Unauthorized"})
    data = await request.json()
    from decimal import Decimal as _Dec
    from app.db import get_session_factory
    from app.models.bonus import BonusTier as _BonusTier
    from sqlalchemy import select as _sel, delete as _del
    async with get_session_factory()() as session:
        await session.execute(_del(_BonusTier))
        for item in data:
            session.add(_BonusTier(
                min_amount=_Dec(str(item["min_amount"])),
                cashback_pct=_Dec(str(item["cashback_pct"])),
            ))
        await session.commit()
        res = await session.execute(_sel(_BonusTier).order_by(_BonusTier.min_amount))
        tiers = res.scalars().all()
    return _JSONResponse({"tiers": [
        {"id": t.id, "min_amount": float(t.min_amount), "cashback_pct": float(t.cashback_pct)}
        for t in tiers
    ]})

@router.post("/admin-api/customer/{user_id}/bonus", include_in_schema=False)
async def admin_customer_bonus(user_id: int, request: Request):
    if request.session.get("admin_token") != "authenticated":
        return _JSONResponse(status_code=401, content={"error": "Unauthorized"})
    if request.session.get("admin_readonly"):
        return _JSONResponse(status_code=403, content={"error": "Readonly"})
    data = await request.json()
    delta = float(data.get("delta", 0))
    if delta == 0:
        return _JSONResponse(status_code=400, content={"error": "delta не может быть 0"})
    note = data.get("note") or None
    reason = "manual_add" if delta > 0 else "manual_deduct"
    from decimal import Decimal as _Dec
    from app.db import get_session_factory
    from app.models.user import User as _User
    from app.models.bonus import BonusTransaction as _BonusTx
    from sqlalchemy import select as _sel
    async with get_session_factory()() as session:
        res = await session.execute(_sel(_User).where(_User.id == user_id))
        user = res.scalar_one_or_none()
        if not user:
            return _JSONResponse(status_code=404, content={"error": "Not found"})
        new_balance = float(user.bonus_balance or 0) + delta
        if new_balance < 0:
            return _JSONResponse(status_code=400, content={"error": "Недостаточно баллов"})
        user.bonus_balance = _Dec(str(new_balance))
        session.add(_BonusTx(user_id=user_id, delta=_Dec(str(delta)), reason=reason, note=note))
        await session.commit()
        await session.refresh(user)
    return _JSONResponse({"ok": True, "bonus_balance": float(user.bonus_balance)})

@router.get("/admin-api/customer/{user_id}/bonus-history", include_in_schema=False)
async def admin_customer_bonus_history(user_id: int, request: Request):
    if request.session.get("admin_token") != "authenticated":
        return _JSONResponse(status_code=401, content={"error": "Unauthorized"})
    from app.db import get_session_factory
    from app.models.bonus import BonusTransaction as _BonusTx
    from sqlalchemy import select as _sel
    async with get_session_factory()() as session:
        res = await session.execute(
            _sel(_BonusTx).where(_BonusTx.user_id == user_id)
            .order_by(_BonusTx.created_at.desc()).limit(10)
        )
        txs = res.scalars().all()
    _REASON_LABELS = {
        "order_cashback": "Кешбэк за заказ", "order_payment": "Списание за заказ",
        "manual_add": "Начислено вручную", "manual_deduct": "Списано вручную",
    }
    rows = []
    for tx in txs:
        d = float(tx.delta)
        sign = "+" if d >= 0 else ""
        cls = "pos" if d >= 0 else "neg"
        rl = _REASON_LABELS.get(tx.reason, tx.reason)
        note = f" · {tx.note}" if tx.note else ""
        from datetime import timezone
        import zoneinfo
        msk = zoneinfo.ZoneInfo("Europe/Moscow")
        dt = tx.created_at.replace(tzinfo=timezone.utc).astimezone(msk).strftime("%d.%m.%Y")
        rows.append(
            f'<div class="btx-row">'
            f'<div class="btx-delta {cls}">{sign}{d:.0f} ₽</div>'
            f'<div class="btx-reason">{rl}{note}</div>'
            f'<div class="btx-date">{dt}</div>'
            f'</div>'
        )
    html = "".join(rows) if rows else \
        '<div style="font-size:12px;color:#9ca3af;text-align:center;padding:8px 0">История пуста</div>'
    return _JSONResponse({"html": html})

@router.post("/admin-api/order/{order_id}/payment-link", include_in_schema=False)
async def admin_order_payment_link(order_id: int, request: Request):
    if request.session.get("admin_token") != "authenticated":
        return _JSONResponse(status_code=401, content={"error": "Unauthorized"})
    if request.session.get("admin_readonly"):
        return _JSONResponse(status_code=403, content={"error": "Readonly"})
    data = await request.json()
    link = (data.get("link") or "").strip()
    if not link.startswith("http"):
        return _JSONResponse(status_code=400, content={"error": "Invalid link"})
    from app.db import get_session_factory
    from sqlalchemy.orm import selectinload
    async with get_session_factory()() as session:
        result = await session.execute(
            select(Order)
            .options(selectinload(Order.user))
            .where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        if not order:
            return _JSONResponse(status_code=404, content={"error": "Not found"})
        order.payment_link = link
        order.status = "awaiting_payment"
        await session.commit()
        # Уведомляем клиента
        if order.user:
            try:
                from app.bot.notify import _send_message
                import asyncio as _asyncio
                _asyncio.create_task(_send_message(
                    order.user.telegram_id,
                    f"👀 Мы увидели ваш заказ <b>{order.number}</b>!\n\n"
                    f"Для оформления перейдите по ссылке на оплату:\n{link}",
                ))
            except Exception:
                pass
    return _JSONResponse({"ok": True})

@router.post("/admin-api/order/{order_id}/tracking", include_in_schema=False)
async def admin_order_tracking(order_id: int, request: Request):
    if request.session.get("admin_token") != "authenticated":
        return _JSONResponse(status_code=401, content={"error": "Unauthorized"})
    if request.session.get("admin_readonly"):
        return _JSONResponse(status_code=403, content={"error": "Readonly"})
    data = await request.json()
    link = (data.get("link") or "").strip()
    from app.db import get_session_factory
    async with get_session_factory()() as session:
        result = await session.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        if not order:
            return _JSONResponse(status_code=404, content={"error": "Not found"})
        order.tracking_link = link
        await session.commit()
    return _JSONResponse({"ok": True})

@router.post("/admin-api/order/{order_id}/feedback", include_in_schema=False)
async def admin_order_feedback(order_id: int, request: Request):
    if request.session.get("admin_token") != "authenticated":
        return _JSONResponse(status_code=401, content={"error": "Unauthorized"})
    from app.db import get_session_factory
    from sqlalchemy.orm import selectinload
    async with get_session_factory()() as session:
        result = await session.execute(
            select(Order)
            .options(selectinload(Order.items), selectinload(Order.user))
            .where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        if not order or not order.user:
            return _JSONResponse(status_code=404, content={"error": "Not found"})
        items_text = ", ".join(
            f"{oi.snapshot_name} {oi.snapshot_weight_g}г" for oi in order.items
        )
        settings = get_settings()
        shop_link = settings.public_base_url.rstrip("/")
        try:
            from app.bot.notify import _send_message
            sent = await _send_message(
                order.user.telegram_id,
                f"Здравствуйте! 🌿\n\n"
                f"Вы заказывали у нас: <b>{items_text}</b>\n\n"
                f"Понравилось ли вам всё? Будем рады вашему отзыву — "
                f"напишите нам прямо здесь или зайдите в магазин:\n{shop_link}",
            )
            if sent:
                from datetime import UTC, datetime as _dt
                order.feedback_sent_at = _dt.now(UTC)
                await session.commit()
        except Exception:
            pass
    return _JSONResponse({"ok": True})

@router.get("/admin-api/me", include_in_schema=False)
async def admin_me(request: Request):
    if request.session.get("admin_token") != "authenticated":
        return _JSONResponse(status_code=401, content={"error": "Unauthorized"})
    return _JSONResponse({
        "username": request.session.get("admin_username", ""),
        "readonly": bool(request.session.get("admin_readonly")),
    })

# ===== ИМПОРТ ТОВАРОВ =====


@router.post("/admin-api/categories/reorder", include_in_schema=False)
async def admin_categories_reorder(request: Request):
    if request.session.get("admin_token") != "authenticated":
        return _JSONResponse(status_code=401, content={"error": "Unauthorized"})
    if request.session.get("admin_readonly"):
        return _JSONResponse(status_code=403, content={"error": "Readonly"})
    data = await request.json()
    ids = data.get("ids", [])
    if not ids:
        return _JSONResponse(status_code=400, content={"error": "ids required"})
    from app.db import get_session_factory
    from app.models.category import Category
    from sqlalchemy import select
    async with get_session_factory()() as session:
        for order, cat_id in enumerate(ids):
            res = await session.execute(select(Category).where(Category.id == cat_id))
            cat = res.scalar_one_or_none()
            if cat:
                cat.sort_order = order
        await session.commit()
    return _JSONResponse({"ok": True})

from fastapi.responses import HTMLResponse as _HTMLResponse, StreamingResponse as _StreamingResponse
import asyncio as _asyncio
import io as _io
from datetime import datetime as _datetime, timezone as _timezone_import


@router.get("/admin-api/import/excel/template", include_in_schema=False)
async def admin_import_excel_template(request: Request):
    if request.session.get("admin_token") != "authenticated":
        return _JSONResponse(status_code=401, content={"error": "Unauthorized"})
    from app.admin.import_worker import make_excel_template
    content = make_excel_template()
    return _StreamingResponse(
        _io.BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=import_template.xlsx"},
    )

@router.post("/admin-api/import/yml", include_in_schema=False)
async def admin_import_yml(request: Request):
    if request.session.get("admin_token") != "authenticated":
        return _JSONResponse(status_code=401, content={"error": "Unauthorized"})
    if request.session.get("admin_readonly"):
        return _JSONResponse(status_code=403, content={"error": "Readonly"})
    data = await request.json()
    url = (data.get("url") or "").strip()
    if not url:
        return _JSONResponse(status_code=400, content={"error": "URL обязателен"})
    from app.db import get_session_factory
    from app.models.yml_import import YmlImport
    from app.admin.import_worker import run_yml_import
    async with get_session_factory()() as session:
        rec = YmlImport(source=url, status="running",
                        started_at=_datetime.now(_timezone_import.utc))
        session.add(rec)
        await session.commit()
        await session.refresh(rec)
        import_id = rec.id
    _asyncio.create_task(run_yml_import(import_id, url))
    return _JSONResponse({"import_id": import_id})

@router.post("/admin-api/import/excel", include_in_schema=False)
async def admin_import_excel(request: Request, file: UploadFile = _File(...)):
    if request.session.get("admin_token") != "authenticated":
        return _JSONResponse(status_code=401, content={"error": "Unauthorized"})
    if request.session.get("admin_readonly"):
        return _JSONResponse(status_code=403, content={"error": "Readonly"})
    content = await file.read()
    from app.db import get_session_factory
    from app.models.yml_import import YmlImport
    from app.admin.import_worker import run_excel_import
    fname = file.filename or "upload.xlsx"
    async with get_session_factory()() as session:
        rec = YmlImport(source=fname, status="running",
                        started_at=_datetime.now(_timezone_import.utc))
        session.add(rec)
        await session.commit()
        await session.refresh(rec)
        import_id = rec.id
    _asyncio.create_task(run_excel_import(import_id, content))
    return _JSONResponse({"import_id": import_id})

@router.get("/admin-api/import/{import_id}/status", include_in_schema=False)
async def admin_import_status(import_id: int, request: Request):
    if request.session.get("admin_token") != "authenticated":
        return _JSONResponse(status_code=401, content={"error": "Unauthorized"})
    from app.db import get_session_factory
    from app.models.yml_import import YmlImport
    from sqlalchemy import select
    async with get_session_factory()() as session:
        rec = (await session.execute(select(YmlImport).where(YmlImport.id == import_id))).scalar_one_or_none()
        if not rec:
            return _JSONResponse(status_code=404, content={"error": "Not found"})
        return _JSONResponse({
            "status": rec.status,
            "products_added": rec.products_added,
            "products_updated": rec.products_updated,
            "images_downloaded": rec.images_downloaded,
            "log": rec.log,
            "error": rec.error,
        })
