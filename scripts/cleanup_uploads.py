"""Удаляет файлы из static/uploads/ не привязанные ни к одному товару в БД.

Запуск на сервере:
    docker compose exec app python3 scripts/cleanup_uploads.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Добавляем backend/ в путь
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
os.environ.setdefault("APP_ENV", "production")

from app.config import get_settings
from app.db import configure_engine, get_session_factory
from app.models.product import ProductImage
from sqlalchemy import select


async def main() -> None:
    settings = get_settings()
    configure_engine(str(settings.database_url))

    async with get_session_factory()() as session:
        rows = (await session.execute(select(ProductImage.path))).scalars().all()

    referenced = {r for r in rows if r}
    uploads_dir = Path(__file__).parent.parent / "backend" / "static" / "uploads"

    if not uploads_dir.exists():
        print("Папка static/uploads/ не найдена")
        return

    deleted = 0
    freed = 0
    orphans = []

    for f in sorted(uploads_dir.iterdir()):
        if not f.is_file():
            continue
        rel = f"/static/uploads/{f.name}"
        if rel not in referenced:
            orphans.append(f)

    if not orphans:
        print("Мусора нет — все файлы привязаны к товарам.")
        return

    print(f"Найдено {len(orphans)} лишних файлов:")
    for f in orphans:
        print(f"  {f.name}  ({f.stat().st_size // 1024} KB)")

    answer = input("\nУдалить? [y/N]: ").strip().lower()
    if answer != "y":
        print("Отменено.")
        return

    for f in orphans:
        freed += f.stat().st_size
        f.unlink()
        deleted += 1

    print(f"\nГотово: удалено {deleted} файлов, освобождено {freed / 1024 / 1024:.1f} MB")


asyncio.run(main())
