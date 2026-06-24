"""Конфигурация приложения (читается из переменных окружения).

Все секреты хранятся ТОЛЬКО в переменных окружения / .env, который
никогда не коммитится (см. .gitignore). Дефолты — безопасные для прода.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения, валидируемые pydantic-settings."""

    # В тестовом режиме (.env не должен влиять на тесты) отключаем чтение файла.
    model_config = SettingsConfigDict(
        env_file=None if os.getenv("APP_ENV") == "test" else ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---------- Режим ----------
    app_env: Literal["development", "production", "test"] = "production"
    debug: bool = False
    log_level: str = "INFO"

    # ---------- Приложение ----------
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    public_base_url: str = "https://example.com"
    cors_origins: str = ""

    # ---------- База данных ----------
    database_url: str = Field(
        default="postgresql+asyncpg://miniteatree:password@db:5432/miniteatree"
    )
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800  # секунд, защита от «протухших» соединений

    # ---------- Telegram ----------
    bot_token: SecretStr = SecretStr("")
    bot_webhook_secret: SecretStr = SecretStr("")  # X-Telegram-Bot-Api-Secret-Token
    admin_telegram_ids: str = ""  # "111,222" → парсим в список
    telegram_api_base_url: str = ""  # прокси для Telegram API (напр. Cloudflare Worker)

    # ---------- Авторизация / JWT ----------
    jwt_secret: SecretStr = SecretStr("")
    jwt_algorithm: str = "HS256"
    jwt_access_ttl_minutes: int = 15
    jwt_refresh_ttl_days: int = 30
    telegram_initdata_max_age_seconds: int = 3600

    # ---------- Реферальная программа ----------
    # ID или @username Telegram-канала для проверки подписки (напр. "@teatree96" или "-1001234567890").
    telegram_channel_id: str = ""
    # Баллы за вступление по реферальной ссылке.
    referral_welcome_bonus: int = 250
    # Велком-слоты, активируемые после первой покупки донора.
    referral_slots_per_donor: int = 2
    # Процент от покупки реципиента, начисляемый донору.
    referral_donor_reward_pct: float = 5.0
    # Максимальное кол-во покупок реципиента, с которых донор получает вознаграждение.
    referral_max_rewarded_purchases: int = 3

    # ---------- Безопасность ----------
    max_upload_bytes: int = 5 * 1024 * 1024  # 5 МБ

    # ---------- Админка (SQLAdmin) ----------
    admin_username: str = "admin"
    admin_password: SecretStr = SecretStr("change_me")

    # ---------- Вспомогательные свойства ----------

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_test(self) -> bool:
        return self.app_env == "test"

    @property
    def cors_origin_list(self) -> list[str]:
        """Список разрешённых CORS-источников (без пустых)."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def admin_telegram_id_list(self) -> list[int]:
        """Список Telegram ID администраторов (числа)."""
        result: list[int] = []
        for raw in self.admin_telegram_ids.split(","):
            raw = raw.strip()
            if not raw:
                continue
            try:
                result.append(int(raw))
            except ValueError:
                continue
        return result

    @field_validator("jwt_secret")
    @classmethod
    def _jwt_secret_must_be_strong(cls, v: SecretStr) -> SecretStr:
        # В test-режиме допускаем короткий секрет (для быстрых тестов).
        # В проде требуем минимум 32 символа.
        value = v.get_secret_value()
        if len(value) < 32:
            raise ValueError("JWT_SECRET должен быть не короче 32 символов")
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Единственный экземпляр настроек (кешируется)."""
    return Settings()  # type: ignore[call-arg]
