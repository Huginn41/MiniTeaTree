# ============================================================
#  MiniTeaTree — Makefile (частые команды)
#  Использование: make <target>
# ============================================================

PYTHON := uv run python
BACKEND := backend
COMPOSE := docker compose
COMPOSE_DEV := $(COMPOSE) -f docker-compose.yml -f docker-compose.dev.yml

.PHONY: help install dev up down logs ps migrate migrate-new test test-cov lint format clean seed

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

seed: ## Залить демо-данные
	cd $(BACKEND) && $(PYTHON) -m app.seed

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
