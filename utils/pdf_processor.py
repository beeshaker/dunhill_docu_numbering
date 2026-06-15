from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF

from .branding import create_faded_logo

# Scan only the top portion of the page for header content.
_HEADER_SCAN_ZONE = 180  # points (~63 mm on A4)

# Minimum detected content height to be treated as a letterhead rather than
# a simple page number or single-line title.
_LETTERHEAD_MIN_HEIGHT = 50  # points (~18 mm)


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


def _detect_header_height(page) -> int:
    """
    Scan the top of the page and return the y-coordinate of the lowest content
    found in the header zone, or 0 if no letterhead is detected.

    Detection criteria (either triggers):
    - An image block exists in the top scan zone (company logo).
    - Three or more text blocks span more than _LETTERHEAD_MIN_HEIGHT points
      (multi-column address/contact layout typical of letterheads).
    Vector drawings (separator lines, borders) in the zone extend the height
    but do not independently trigger detection.
    """
    max_y = 0.0
    has_image = False
    text_block_count = 0

    for block in page.get_text("dict")["blocks"]:
        x0, y0, x1, y1 = block["bbox"]
        if y0 >= _HEADER_SCAN_ZONE:
            continue
        if block["type"] == 1:  # image
            has_image = True
        else:
            text_block_count += 1
        max_y = max(max_y, y1)

    # Include separator lines / decorative rules drawn in the header zone.
    for drawing in page.get_drawings():
        drect = drawing.get("rect")
        if drect and drect.y0 < _HEADER_SCAN_ZONE:
            max_y = max(max_y, drect.y1)

    is_letterhead = has_image or (text_block_count >= 3 and max_y > _LETTERHEAD_MIN_HEIGHT)
    return int(max_y) if is_letterhead else 0


def insert_reference_pdf(
    input_path: Path,
    output_path: Path,
    reference_number: str,
    *,
    add_watermark: bool = False,
    logo_path: Path | None = None,
    letterhead_pdf_bytes: bytes | None = None,
    letterhead_header_height: int = 0,
) -> Path:
    doc = fitz.open(str(input_path))
    header_text = f"Ref No.: {reference_number}"
    watermark_path = create_faded_logo(logo_path, opacity=0.10) if add_watermark else None

    lh_doc = fitz.open("pdf", letterhead_pdf_bytes) if letterhead_pdf_bytes else None

    try:
        for page in doc:
            if lh_doc:
                # Merge letterhead as a background underlay so document content
                # remains on top. Use the first page of the letterhead for every
                # page of the document (standard letterhead behaviour).
                page.show_pdf_page(
                    page.rect,
                    lh_doc,
                    0,
                    overlay=False,
                )

            if watermark_path:
                _insert_logo_watermark(page, watermark_path)

            rect = page.rect

            # Manual override takes priority; otherwise auto-detect from page content.
            # When a letterhead was just merged in, always scan — the merge makes the
            # letterhead content visible to the block detector.
            effective_height = letterhead_header_height or _detect_header_height(page)

            if effective_height > 0:
                # Place below the detected/configured letterhead, left-aligned
                # like a standard "Our Ref:" line in a business letter.
                x = 36
                y = effective_height + 14
            else:
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
        if lh_doc:
            lh_doc.close()

    return output_path
