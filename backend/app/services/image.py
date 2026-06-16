"""Сервис работы с изображениями: скачивание, валидация, сохранение."""

from __future__ import annotations

import io
from pathlib import Path

import httpx
from PIL import Image

from app.config import get_settings
from app.logging import get_logger

log = get_logger("services.image")

# Допустимые форматы.
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_DIMENSION = 4096  # px


def _validate_image(data: bytes, max_bytes: int) -> Image.Image:
    """Проверяет формат, размер, открывает PIL Image."""
    if len(data) > max_bytes:
        raise ValueError(f"Image too large: {len(data)} > {max_bytes} bytes")

    try:
        img = Image.open(io.BytesIO(data))
        img.verify()
    except Exception as exc:
        raise ValueError(f"Invalid image: {exc}") from exc

    # Переоткрываем после verify (PIL закрывает файл).
    img = Image.open(io.BytesIO(data))

    fmt = img.format or ""
    ext = f".{fmt.lower()}"
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported format: {fmt}")

    if img.width > MAX_DIMENSION or img.height > MAX_DIMENSION:
        raise ValueError(
            f"Image too large: {img.width}x{img.height} > {MAX_DIMENSION}px"
        )

    return img


def _resize_if_needed(img: Image.Image, max_px: int = 1200) -> Image.Image:
    """Уменьшает изображение, если оно больше max_px по любой стороне."""
    if img.width <= max_px and img.height <= max_px:
        return img
    img.thumbnail((max_px, max_px), Image.Resampling.LANCZOS)
    return img


async def download_image(url: str, save_dir: Path) -> str:
    """Скачивает картинку по URL, валидирует, ресайзит, сохраняет.

    Возвращает относительный путь (например, "products/abc123.jpg").
    """
    settings = get_settings()
    max_bytes = settings.max_upload_bytes

    log.info("image_download_start", url=url)
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
    data = resp.content

    img = _validate_image(data, max_bytes)
    img = _resize_if_needed(img)

    save_dir.mkdir(parents=True, exist_ok=True)

    fmt = (img.format or "JPEG").lower()
    ext = f".{fmt}" if fmt in {"jpeg", "png", "webp", "gif"} else ".jpg"

    # Уникальное имя (sha256 — безопаснее для file naming).
    import hashlib

    filename = hashlib.sha256(data).hexdigest()[:16] + ext
    filepath = save_dir / filename
    filepath.write_bytes(io.BytesIO() or b"")

    # Сохраняем через PIL для нормализации.
    buf = io.BytesIO()
    if fmt == "png":
        img.save(buf, format="PNG", optimize=True)
    elif fmt == "webp":
        img.save(buf, format="WEBP", quality=85)
    else:
        img.save(buf, format="JPEG", quality=85, optimize=True)
    filepath.write_bytes(buf.getvalue())

    relative = str(filepath.relative_to(save_dir.parent.parent / "media"))
    log.info("image_saved", path=relative, size=filepath.stat().st_size)
    return relative
