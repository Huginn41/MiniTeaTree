# DEPLOY.md — Инструкция по деплою «Чайное Дерево»

## Требования к серверу

- Ubuntu 22.04+ / Debian 12+
- Docker + Docker Compose v2 (`docker compose`)
- Домен с DNS A-записью → IP сервера
- Открытые порты: 80, 443

---

## 1. Подготовка сервера

```bash
# Установка Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
```

---

## 2. Клонирование репозитория

```bash
git clone https://github.com/your-org/MiniTeaTree.git /opt/miniteatree
cd /opt/miniteatree
```

---

## 3. Конфигурация `.env`

Скопируй шаблон и заполни все переменные:

```bash
cp .env.example .env
nano .env
```

### Обязательные переменные

```env
# Режим
APP_ENV=production
DEBUG=false
LOG_LEVEL=INFO

# База данных
POSTGRES_USER=miniteatree
POSTGRES_PASSWORD=<сгенерируй: openssl rand -hex 20>
POSTGRES_DB=miniteatree
DATABASE_URL=postgresql+asyncpg://miniteatree:<пароль>@db:5432/miniteatree

# Публичный URL (без слеша в конце)
PUBLIC_BASE_URL=https://your-domain.com

# CORS (URL Telegram Mini App = тот же домен)
CORS_ORIGINS=https://your-domain.com

# Telegram
BOT_TOKEN=<токен от @BotFather>
ADMIN_TELEGRAM_IDS=<твой telegram_id через запятую>

# JWT (минимум 32 символа)
JWT_SECRET=<openssl rand -hex 32>
JWT_ALGORITHM=HS256
JWT_ACCESS_TTL_MINUTES=15
JWT_REFRESH_TTL_DAYS=30
TELEGRAM_INITDATA_MAX_AGE_SECONDS=86400

# Платежи ЮKassa
YOOKASSA_PROVIDER_TOKEN=<токен от @BotFather → Payments → ЮKassa>
YOOKASSA_SHOP_ID=<shop_id из кабинета ЮKassa>
YOOKASSA_SECRET_KEY=<secret_key из кабинета ЮKassa>
YOOKASSA_WEBHOOK_URL=https://your-domain.com/api/payments/webhook/yookassa

# Загрузка файлов
MAX_UPLOAD_BYTES=5242880

# Админ-панель (/admin)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<придумай надёжный пароль>
```

---

## 4. TLS-сертификат (Let's Encrypt)

```bash
# Установить certbot
sudo apt install certbot

# Получить сертификат (nginx должен быть остановлен)
sudo certbot certonly --standalone -d your-domain.com

# Скопировать в нужное место
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem nginx/ssl/key.pem
sudo chown $USER:$USER nginx/ssl/*.pem
```

Автообновление:

```bash
# /etc/cron.d/certbot-renew
0 3 * * 1 root certbot renew --quiet && \
  cp /etc/letsencrypt/live/your-domain.com/fullchain.pem /opt/miniteatree/nginx/ssl/cert.pem && \
  cp /etc/letsencrypt/live/your-domain.com/privkey.pem /opt/miniteatree/nginx/ssl/key.pem && \
  docker compose -f /opt/miniteatree/docker-compose.yml exec nginx nginx -s reload
```

---

## 5. Первый запуск

```bash
cd /opt/miniteatree

# Собрать образы
docker compose build

# Запустить БД отдельно (чтобы применить миграции)
docker compose up -d db
sleep 5

# Применить миграции
docker compose run --rm app alembic upgrade head

# Залить демо-данные (опционально)
docker compose run --rm app python -m app.seed

# Запустить всё
docker compose up -d
```

---

## 6. Настройка Telegram Bot Webhook

После запуска зарегистрируй webhook:

```bash
# Основной webhook для команд бота (/start и т.д.)
curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-domain.com/bot/webhook"}'

# Убедись, что всё ОК
curl "https://api.telegram.org/bot<BOT_TOKEN>/getWebhookInfo"
```

> **Важно:** Для Telegram Payments pre_checkout_query обрабатывается через тот же `/bot/webhook`.
> Отдельный URL для платёжного webhook не нужен — всё через основной webhook бота.

---

## 7. Настройка Mini App в BotFather

```
/newapp  → выбери бота
→ Short name: teatree (или любое)
→ URL: https://your-domain.com/frontend/index.html
```

Или через кнопку в /start (уже реализовано в боте).

---

## 8. Создание первого администратора

Войди в SQLAdmin через `.env` (`ADMIN_USERNAME` / `ADMIN_PASSWORD`):

```
https://your-domain.com/admin
```

Либо создай AdminUser через shell:

```bash
docker compose run --rm app python -c "
import asyncio
from passlib.context import CryptContext
from app.db import configure_engine, get_session_factory
from app.models.admin import AdminUser

async def main():
    configure_engine()
    pwd = CryptContext(schemes=['bcrypt']).hash('твой_пароль')
    async with get_session_factory()() as s:
        s.add(AdminUser(username='admin', password_hash=pwd, is_superuser=True))
        await s.commit()
        print('Admin created')

asyncio.run(main())
"
```

---

## 9. Обновление приложения

```bash
cd /opt/miniteatree
git pull
docker compose build app
docker compose run --rm app alembic upgrade head
docker compose up -d app
```

---

## 10. Полезные команды

```bash
# Логи
docker compose logs -f app
docker compose logs -f nginx

# Статус
docker compose ps

# Перезапустить только приложение
docker compose restart app

# Сделать резервную копию БД
docker compose exec db pg_dump -U miniteatree miniteatree > backup_$(date +%Y%m%d).sql

# Восстановить БД из бэкапа
docker compose exec -T db psql -U miniteatree miniteatree < backup_YYYYMMDD.sql

# Зайти в shell приложения
docker compose exec app python
```

---

## Структура данных для первичной настройки

После деплоя через SQLAdmin (`/admin`) нужно заполнить:

1. **Категории** — хотя бы одна для отображения каталога
2. **Товары и варианты** — импорт через YML или вручную
3. **Уведомления** → NotificationTarget — telegram_id менеджера, роль `manager`
4. **FAQ и баннеры** — опционально, для главной страницы

---

## Переменные окружения для dev-режима

```bash
# Локальная разработка без docker
cd backend
cp .env.example .env
# Установить APP_ENV=development, DATABASE_URL=sqlite+aiosqlite:///./dev.db

uv sync
uv run alembic upgrade head
uv run python -m app.seed
uv run uvicorn app.main:app --reload
```
