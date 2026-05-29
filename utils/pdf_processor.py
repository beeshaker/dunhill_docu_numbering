from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF

from .branding import create_faded_logo


def _insert_logo_watermark(page, watermark_path: Path) -> None:
    rect = page.rect
    pix = fitz.Pixmap(str(watermark_path))

    target_width = min(rect.width * 0.60, pix.width * 0.75)
    scale = target_width / max(pix.width, 1)
    target_height = pix.height * scale

    x0 = (rect.width - target_width) / 2
    y0 = (rect.height - target_height) / 2
    watermark_rect = fitz.Rect(x0, y0, x0 + target_width, y0 + target_height)

    page.insert_image(
        watermark_rect,
        filename=str(watermark_path),
        overlay=True,
        keep_proportion=True,
    )


def insert_reference_pdf(
    input_path: Path,
    output_path: Path,
    reference_number: str,
    *,
    add_watermark: bool = False,
    logo_path: Path | None = None,
) -> Path:
    doc = fitz.open(str(input_path))
    header_text = f"Ref No.: {reference_number}"
    watermark_path = create_faded_logo(logo_path, opacity=0.10) if add_watermark else None

    try:
        for page in doc:
            if watermark_path:
                _insert_logo_watermark(page, watermark_path)

            rect = page.rect
            x = max(rect.width - 220, 36)
            y = 24
            page.insert_text(
                (x, y),
                header_text,
                fontsize=9,
                fontname="helv",
                overlay=True,
            )

        doc.save(str(output_path), garbage=4, deflate=True)
    finally:
        doc.close()

    return output_path
