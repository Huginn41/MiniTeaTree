"""Тесты мета-эндпоинтов: healthcheck (liveness) и readiness."""

from __future__ import annotations

from httpx import AsyncClient


async def test_health_liveness(client: AsyncClient) -> None:
    """GET /health возвращает 200 и статус ok."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body


async def test_api_root(client: AsyncClient) -> None:
    """GET /api/ отдаёт имя и версию API."""
    resp = await client.get("/api/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "MiniTeaTree API"
    assert "version" in body
