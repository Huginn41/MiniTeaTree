# ============================================================
#  MiniTeaTree — Makefile (частые команды)
#  Использование: make <target>
# ============================================================

PYTHON := uv run python
BACKEND := backend
COMPOSE := docker compose
COMPOSE_DEV := $(COMPOSE) -f docker-compose.yml -f docker-compose.dev.yml

.PHONY: help install dev up down logs ps migrate migrate-new test test-cov lint format clean seed seed-demo demo-up demo-down demo-seed demo-logs

help: ## Показать список команд
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ---------- Локальная разработка (без docker, через uv) ----------
install: ## Установить зависимости (uv sync)
	cd $(BACKEND) && uv sync

dev: ## Поднять dev-окружение в docker (с хот-релоадом)
	$(COMPOSE_DEV) up -d --build

up: ## Поднять prod-окружение в docker
	$(COMPOSE) up -d --build

down: ## Остановить контейнеры
	$(COMPOSE) down

logs: ## Логи всех сервисов (tail -f)
	$(COMPOSE) logs -f --tail=100

ps: ## Статус контейнеров
	$(COMPOSE) ps

# ---------- База данных ----------
migrate: ## Применить миграции alembic upgrade head
	cd $(BACKEND) && $(PYTHON) -m alembic upgrade head

migrate-new: ## Создать новую миграцию: make migrate-new m="message"
	cd $(BACKEND) && $(PYTHON) -m alembic revision --autogenerate -m "$(m)"

seed: ## Залить базовые данные (каталог, FAQ, баннеры)
	cd $(BACKEND) && $(PYTHON) -m app.seed

seed-demo: ## Залить моковые данные (login: demo / demo1234 → DEMO-заказы)
	cd $(BACKEND) && $(PYTHON) -m app.demo_seed

clean-demo: ## Удалить все демо-данные из БД (DEMO-заказы + демо-клиенты)
	docker compose exec app python -m app.demo_clean

# ---------- Тесты и качество ----------
test: ## Запустить тесты
	cd $(BACKEND) && $(PYTHON) -m pytest -q

test-cov: ## Запустить тесты с покрытием
	cd $(BACKEND) && $(PYTHON) -m pytest --cov=app --cov-report=term-missing

lint: ## Линтинг (ruff)
	cd $(BACKEND) && $(PYTHON) -m ruff check app tests

format: ## Форматирование кода (ruff)
	cd $(BACKEND) && $(PYTHON) -m ruff format app tests && $(PYTHON) -m ruff check --fix app tests

clean: ## Удалить артефакты (кэш, __pycache__)
	find $(BACKEND) -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find $(BACKEND) -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf $(BACKEND)/.coverage $(BACKEND)/htmlcov 2>/dev/null || true

# ---------- Demo-окружение (изолированная БД на порту 5433/8001) ----------
COMPOSE_DEMO := $(COMPOSE) -f docker-compose.demo.yml --env-file .env.demo

demo-up: ## Поднять demo-окружение (cp .env.demo.example .env.demo сначала)
	$(COMPOSE_DEMO) up -d --build

demo-down: ## Остановить demo-окружение
	$(COMPOSE_DEMO) down

demo-seed: ## Залить демо-данные (60 заказов, 15 товаров с эмодзи)
	$(COMPOSE_DEMO) exec app uv run python -m app.demo_seed

demo-logs: ## Логи demo-окружения
	$(COMPOSE_DEMO) logs -f --tail=100
