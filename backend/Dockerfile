# ============================================================
#  Multi-stage Dockerfile для backend
# ============================================================

# ---------- Сборка зависимостей ----------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_SYSTEM_PYTHON=1

# Системные библиотеки для сборки (Pillow, lxml, asyncpg, bcrypt)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libxml2-dev \
        libxslt1-dev \
        libjpeg-dev \
        zlib1g-dev \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# uv — быстрый resolver/installe
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Сначала только зависимости — для кэширования слоя
COPY pyproject.toml ./
RUN uv pip install --system --no-cache .

# ---------- Runtime (prod) ----------
FROM python:3.12-slim AS prod

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Только runtime-библиотеки
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        libxml2 \
        libxslt1.1 \
        libjpeg62-turbo \
        zlib1g \
        curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 10001 appuser

WORKDIR /app

# Копируем установленные пакеты из builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Копируем код приложения
COPY --chown=appuser:appuser . /app

# Директории под медиа
RUN mkdir -p /app/app/static/media/products /app/app/static/media/banners \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

# Применяем миграции и стартуем uvicorn под gunicorn
CMD ["sh", "-c", "alembic upgrade head && gunicorn app.main:app -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 -w 2 --timeout 120"]

# ---------- Dev (hot reload) ----------
FROM prod AS dev

USER root

# В dev нужны dev-зависимости (pytest/ruff) и работа от root для volume
COPY pyproject.toml ./
RUN uv pip install --system --no-cache ".[dev]"

USER appuser
