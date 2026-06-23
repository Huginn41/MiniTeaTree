"""Точка входа для регистрации всех маршрутов кастомного дашборда."""

from __future__ import annotations

from fastapi import FastAPI

from app.admin.pages.about import setup_about_routes
from app.admin.pages.dashboard import setup_dashboard_routes
from app.admin.pages.orders import setup_orders_routes

# Реэкспорт для обратной совместимости с bonus_settings.py и другими модулями,
# которые могут импортировать _topnav/_BASE_CSS напрямую.
from app.admin.shared import _BASE_CSS, _STATUS_LABELS_JS, _render, _topnav

__all__ = ["setup_dashboard", "_topnav", "_BASE_CSS", "_STATUS_LABELS_JS", "_render"]


def setup_dashboard(app: FastAPI) -> None:
    setup_dashboard_routes(app)
    setup_orders_routes(app)
    setup_about_routes(app)
