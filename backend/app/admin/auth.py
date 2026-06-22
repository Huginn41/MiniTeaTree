"""Аутентификация администратора."""

from __future__ import annotations

import bcrypt as _bcrypt
from sqladmin.authentication import AuthenticationBackend
from sqlalchemy import select
from starlette.requests import Request


class AdminAuth(AuthenticationBackend):
    async def authenticate(self, request: Request) -> bool:
        return request.session.get("admin_token") == "authenticated"

    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = str(form.get("username", ""))
        password = str(form.get("password", ""))

        from app.config import get_settings
        from app.db import get_session_factory
        from app.models.admin import AdminUser

        async with get_session_factory()() as session:
            result = await session.execute(
                select(AdminUser).where(AdminUser.username == username)
            )
            admin = result.scalar_one_or_none()

        if admin is None:
            settings = get_settings()
            if username == settings.admin_username and password == settings.admin_password.get_secret_value():
                request.session["admin_token"] = "authenticated"
                request.session["admin_username"] = username
                return True
            return False

        if not _bcrypt.checkpw(password.encode(), admin.password_hash.encode()):
            return False

        request.session["admin_token"] = "authenticated"
        request.session["admin_username"] = admin.username
        request.session["admin_readonly"] = not admin.is_superuser
        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True


def require_admin(request: Request) -> bool:
    """Возвращает True если сессия аутентифицирована."""
    return request.session.get("admin_token") == "authenticated"
