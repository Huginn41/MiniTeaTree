"""Очистка и миграция файлов uploads.

Запуск на сервере:
    docker compose exec -it app python3 scripts/cleanup_uploads.py
"""

import asyncio
import shutil
from pathlib import Path

from app.config import get_settings
from app.db import configure_engine, get_session_factory
from app.models.product import ProductImage
from sqlalchemy import select, update


async def main() -> None:
    settings = get_settings()
    configure_engine(str(settings.database_url))

    # Папки
    app_dir = Path(__file__).parent.parent / "app"
    old_dir = Path(__file__).parent.parent / "static" / "uploads"
    new_dir = app_dir / "static" / "media" / "uploads"
    new_dir.mkdir(parents=True, exist_ok=True)

    async with get_session_factory()() as session:

        # ── 1. Миграция старых файлов /static/uploads/ → /static/media/uploads/ ──
        if old_dir.exists() and any(old_dir.iterdir()):
            old_imgs = (await session.execute(
                select(ProductImage).where(ProductImage.path.like("/static/uploads/%"))
            )).scalars().all()

            migrated = 0
            for img in old_imgs:
                fname = img.path.split("/")[-1]
                src = old_dir / fname
                dst = new_dir / fname
                if src.exists():
                    shutil.move(str(src), str(dst))
                    img.path = f"/static/media/uploads/{fname}"
                    migrated += 1

            if migrated:
                await session.commit()
                print(f"Мигрировано {migrated} файлов в /static/media/uploads/")
            else:
                print("Старых файлов для миграции нет.")
        else:
            print("Папка /static/uploads/ пуста или не существует.")

        # ── 2. Очистка мусора в /static/media/uploads/ ──
        rows = (await session.execute(select(ProductImage.path))).scalars().all()

    referenced = {r for r in rows if r}

    orphans = [
        f for f in sorted(new_dir.iterdir())
        if f.is_file() and f"/static/media/uploads/{f.name}" not in referenced
    ]

    if not orphans:
        print("Мусора нет — все файлы привязаны к товарам.")
        return

    print(f"\nНайдено {len(orphans)} лишних файлов:")
    for f in orphans:
        print(f"  {f.name}  ({f.stat().st_size // 1024} KB)")

    answer = input("\nУдалить? [y/N]: ").strip().lower()
    if answer != "y":
        print("Отменено.")
        return

    freed = sum(f.stat().st_size for f in orphans)
    for f in orphans:
        f.unlink()

    print(f"Готово: удалено {len(orphans)} файлов, освобождено {freed / 1024 / 1024:.1f} MB")


asyncio.run(main())
