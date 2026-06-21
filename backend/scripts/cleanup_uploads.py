"""Удаляет файлы из static/uploads/ не привязанные ни к одному товару в БД.

Запуск на сервере:
    docker compose exec app python3 scripts/cleanup_uploads.py
"""

import asyncio
from pathlib import Path

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
    uploads_dir = Path(__file__).parent.parent / "static" / "uploads"

    if not uploads_dir.exists():
        print("Папка static/uploads/ не найдена")
        return

    orphans = [
        f for f in sorted(uploads_dir.iterdir())
        if f.is_file() and f"/static/uploads/{f.name}" not in referenced
    ]

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

    freed = 0
    for f in orphans:
        freed += f.stat().st_size
        f.unlink()

    print(f"\nГотово: удалено {len(orphans)} файлов, освобождено {freed / 1024 / 1024:.1f} MB")


asyncio.run(main())
