from __future__ import annotations

from pathlib import Path

from .excel_processor import insert_reference_excel
from .pdf_processor import insert_reference_pdf
from .word_processor import insert_reference_docx


def process_document_file(
    input_path: Path,
    output_path: Path,
    reference_number: str,
    add_watermark: bool = False,
    letterhead_header_height: int = 0,
):
    """Stamp the generated reference into Word, PDF, or Excel files."""
    suffix = input_path.suffix.lower()

    if suffix == ".docx":
        return insert_reference_docx(
            input_path,
            output_path,
            reference_number,
            add_watermark=add_watermark,
        )

    if suffix == ".pdf":
        return insert_reference_pdf(
            input_path,
            output_path,
            reference_number,
            add_watermark=add_watermark,
            letterhead_header_height=letterhead_header_height,
        )

    if suffix == ".xlsx":
        return insert_reference_excel(
            input_path,
            output_path,
            reference_number,
            add_watermark=add_watermark,
        )

    raise ValueError("Unsupported file type. Please upload .docx, .pdf, or .xlsx.")
