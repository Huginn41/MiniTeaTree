# Деплой демо-окружения

Демо полностью изолировано: своя PostgreSQL, свои данные, отдельный поддомен.

## Архитектура

```
demo.DOMAIN  →  nginx (443)  →  miniteatree_demo_app:8000  →  demo_postgres
   DOMAIN     →  nginx (443)  →  miniteatree_app:8000        →  postgres (прод)
```

Оба приложения работают на одном сервере. nginx видит оба через общую сеть `internal`.

---

## 1. DNS

Добавь A-запись на том же IP что и основной домен:

```
demo.xn--80aefdbay6ajft0f.xn--p1ai  →  <IP сервера>
```

---

## 2. TLS-сертификат для поддомена

На сервере:

```bash
certbot certonly --nginx -d demo.xn--80aefdbay6ajft0f.xn--p1ai
```

---

## 3. Конфиг демо

```bash
cp .env.demo.example .env.demo
# отредактируй .env.demo: проверь DATABASE_URL и JWT_SECRET
```

Минимальные изменения в `.env.demo`:
```
JWT_SECRET=<случайная строка 32+ символов>
DATABASE_URL=postgresql+asyncpg://demo_user:demo_pass@demo_db:5432/teatree_demo
```

---

## 4. Запуск

```bash
# Убедись что основной прод уже запущен (нужна сеть "internal"):
docker compose up -d

# Поднять демо:
make demo-up

# Залить данные (60 заказов, 15 товаров):
make demo-seed

# Перезапустить nginx (подхватит demo_backend):
docker compose restart nginx
```

---

## 5. Проверка

- Демо-админка: `https://demo.xn--80aefdbay6ajft0f.xn--p1ai/admin/`
  - Полный доступ: `admin / demo1234`
  - Read-only:     `demo / demo1234`

---

## Обновление демо-данных

Пересеять данные (идемпотентно):
```bash
make demo-seed
```

Полный сброс (удалить БД и пересоздать):
```bash
make demo-down
docker volume rm miniteatree_demo_postgres_data
make demo-up
make demo-seed
```

---

## Остановка

```bash
make demo-down
```

Прод-данные не затрагиваются.
