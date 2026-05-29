from __future__ import annotations

from pathlib import Path

try:
    from PIL import Image, ImageEnhance
except Exception:  # pragma: no cover
    Image = None
    ImageEnhance = None

MODULE_DIR = Path(__file__).resolve().parents[1]
ASSETS_DIR = MODULE_DIR / "static" / "src" / "img"
STORAGE_DIR = MODULE_DIR / "storage"
GENERATED_DIR = STORAGE_DIR / "generated"
LOGO_PATH = ASSETS_DIR / "dunhill_logo.png"

GENERATED_DIR.mkdir(parents=True, exist_ok=True)


def get_logo_path() -> Path | None:
    """Return the bundled company logo path if it exists."""
    return LOGO_PATH if LOGO_PATH.exists() else None


def create_faded_logo(
    logo_path: Path | None = None,
    *,
    opacity: float = 0.12,
    max_width_px: int = 900,
    output_name: str = "_dunhill_watermark.png",
) -> Path | None:
    """Create a transparent/faded PNG suitable for watermarking.

    Returns None if there is no logo or Pillow is not available. This keeps
    document generation working even when watermarking dependencies are missing.
    """
    if Image is None or ImageEnhance is None:
        return None

    logo_path = logo_path or get_logo_path()
    if not logo_path or not logo_path.exists():
        return None

    output_path = GENERATED_DIR / output_name

    img = Image.open(logo_path).convert("RGBA")

    if img.width > max_width_px:
        ratio = max_width_px / float(img.width)
        new_size = (max_width_px, max(1, int(img.height * ratio)))
        img = img.resize(new_size, Image.LANCZOS)

    rgb = Image.new("RGBA", img.size, (255, 255, 255, 0))
    rgb.alpha_composite(img)
    alpha = rgb.getchannel("A")
    alpha = ImageEnhance.Brightness(alpha).enhance(max(0.0, min(opacity, 1.0)))
    rgb.putalpha(alpha)

    rgb.save(output_path)
    return output_path
