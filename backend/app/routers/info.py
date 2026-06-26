"""Роутер справочного контента: баннеры, FAQ, ПВЗ."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.banner import Banner
from app.models.bonus import ShopSettings
from app.models.content import FaqItem, PickupPoint, SiteAbout
from app.schemas import BannerOut, FaqItemOut, PickupPointOut, SiteAboutOut

router = APIRouter(prefix="/info", tags=["info"])


@router.get("/banners", response_model=list[BannerOut])
async def list_banners(
    session: AsyncSession = Depends(get_db),
) -> list[BannerOut]:
    """Активные баннеры для главной (по sort)."""
    stmt = (
        select(Banner)
        .where(Banner.is_active.is_(True), Banner.is_demo.is_(False))
        .order_by(Banner.sort, Banner.id)
    )
    result = await session.execute(stmt)
    return [BannerOut.model_validate(b) for b in result.scalars().all()]


@router.get("/faq", response_model=list[FaqItemOut])
async def list_faq(
    session: AsyncSession = Depends(get_db),
) -> list[FaqItemOut]:
    """FAQ — вопросы и ответы."""
    stmt = (
        select(FaqItem)
        .where(FaqItem.is_active.is_(True), FaqItem.is_demo.is_(False))
        .order_by(FaqItem.sort, FaqItem.id)
    )
    result = await session.execute(stmt)
    return [FaqItemOut.model_validate(f) for f in result.scalars().all()]


@router.get("/about", response_model=SiteAboutOut)
async def get_about(session: AsyncSession = Depends(get_db)) -> SiteAboutOut:
    """Содержимое страницы О нас."""
    result = await session.execute(select(SiteAbout).where(SiteAbout.id == 1))
    about = result.scalar_one_or_none()
    if not about:
        return SiteAboutOut()
    return SiteAboutOut.model_validate(about)


@router.get("/bonus-config")
async def get_bonus_config(session: AsyncSession = Depends(get_db)) -> dict:
    """Публичная конфигурация бонусной системы (макс. % оплаты баллами)."""
    stmt = select(ShopSettings).where(ShopSettings.id == 1)
    result = await session.execute(stmt)
    s = result.scalar_one_or_none()
    return {"max_payment_pct": s.bonus_max_payment_pct if s else 0}


@router.get("/pickup-points", response_model=list[PickupPointOut])
async def list_pickup_points(
    session: AsyncSession = Depends(get_db),
) -> list[PickupPointOut]:
    """Список активных ПВЗ."""
    stmt = (
        select(PickupPoint)
        .where(PickupPoint.is_active.is_(True), PickupPoint.is_demo.is_(False))
        .order_by(PickupPoint.sort_order, PickupPoint.id)
    )
    result = await session.execute(stmt)
    return [PickupPointOut.model_validate(p) for p in result.scalars().all()]
