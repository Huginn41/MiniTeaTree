"""SQLAdmin — панель администратора Чайного Дерева."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI
from sqladmin import Admin
from sqladmin import widgets as _sqladmin_widgets

# wtforms 3.2+ добавил validation_attrs, sqladmin 0.27 этого не знает
if not hasattr(_sqladmin_widgets.BooleanInputWidget, "validation_attrs"):
    _sqladmin_widgets.BooleanInputWidget.validation_attrs = []


def setup_admin(app: FastAPI, engine: Any) -> None:
    from app.admin.dashboard import setup_dashboard
    from app.admin.auth import AdminAuth
    from app.admin.inject import _AdminCollapseMiddleware
    from app.admin.router import router as admin_router
    from app.admin.model_views import (
        OrderAdmin, OrderItemAdmin, DeliveryInfoAdmin,
        UserAdmin, NotificationTargetAdmin,
        ProductAdmin, CategoryAdmin, BannerAdmin, PickupPointAdmin,
        AdminUserAdmin, YmlImportAdmin, PaymentEventAdmin,
        BonusSettingsView,
    )
    from app.config import get_settings

    setup_dashboard(app)

    # Кастомные роуты ПЕРЕД Admin.mount("/admin") — иначе SQLAdmin перехватит их первым
    app.include_router(admin_router)

    settings = get_settings()
    authentication_backend = AdminAuth(secret_key=settings.jwt_secret.get_secret_value())
    _templates_dir = str(Path(__file__).parent / "templates")

    admin = Admin(
        app=app,
        engine=engine,
        authentication_backend=authentication_backend,
        title="Чайное Дерево",
        base_url="/admin",
        templates_dir=_templates_dir,
    )

    # Заказы
    admin.add_view(OrderAdmin)
    admin.add_view(OrderItemAdmin)
    admin.add_view(DeliveryInfoAdmin)
    # CRM
    admin.add_view(UserAdmin)
    admin.add_view(NotificationTargetAdmin)
    # Настройки магазина
    admin.add_view(ProductAdmin)
    admin.add_view(CategoryAdmin)
    admin.add_view(BannerAdmin)
    admin.add_view(PickupPointAdmin)
    admin.add_view(BonusSettingsView)
    # Система
    admin.add_view(AdminUserAdmin)
    admin.add_view(YmlImportAdmin)
    admin.add_view(PaymentEventAdmin)
