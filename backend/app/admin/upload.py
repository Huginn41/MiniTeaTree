"""Утилиты загрузки и обработки изображений."""

from __future__ import annotations

from pathlib import Path

UPLOADS_DIR = Path(__file__).parent.parent.parent / "static" / "media" / "uploads"
MAX_IMAGE_PX = 1600
UPLOAD_MAX_BYTES = 15 * 1024 * 1024  # совпадает с nginx client_max_body_size


def to_webp(data: bytes, dest: Path, max_px: int = MAX_IMAGE_PX) -> None:
    """Конвертирует изображение в WebP с ограничением размера."""
    from PIL import Image, UnidentifiedImageError
    import io as _io

    try:
        img = Image.open(_io.BytesIO(data))
        img.load()
    except (UnidentifiedImageError, Exception) as exc:
        raise ValueError(f"Не удалось открыть изображение: {exc}") from exc

    if img.mode != "RGB":
        rgba = img.convert("RGBA")
        bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        img = Image.alpha_composite(bg, rgba).convert("RGB")

    w, h = img.size
    if max(w, h) > max_px:
        r = max_px / max(w, h)
        img = img.resize((int(w * r), int(h * r)), Image.LANCZOS)

    img.save(dest, "WEBP", quality=85, method=4)


def delete_upload_file(path: str | None) -> None:
    """Удаляет файл из static/uploads/ если он там лежит."""
    if not path:
        return
    if not path.startswith("/static/media/uploads/"):
        return
    file = Path(__file__).parent.parent.parent / path.lstrip("/")
    try:
        file.unlink(missing_ok=True)
    except Exception:
        pass
