"""
PaperVerify — Stage 1: PDF Ingestion.

Extracts text page-by-page from PDFs with support for:
- Multi-column academic layouts (layout-aware block sorting)
- OCR fallback for scanned/image-only pages
- Table/figure caption detection
- Corrupted/password-protected PDF handling
- Language detection
"""
import re
from pathlib import Path

import fitz  # PyMuPDF

from models.schemas import PageText, DocumentResult
from utils.language import detect_language
from utils.logging_util import logger

# ── Caption patterns ──────────────────────────────────────────────────
TABLE_CAPTION_RE = re.compile(
    r"(?:Table|TABLE|Tabla|Tabelle)\s+\d+[\.:]\s*.{5,120}", re.IGNORECASE
)
FIGURE_CAPTION_RE = re.compile(
    r"(?:Fig(?:ure)?|FIGURE|Figura|Abbildung)\.?\s+\d+[\.:]\s*.{5,120}", re.IGNORECASE
)


def _try_ocr(page: fitz.Page) -> tuple[str, bool]:
    """
    Attempt OCR on a page image using pytesseract.
    Returns (text, success).
    """
    try:
        import pytesseract
        from PIL import Image
        import io

        # Render page to image at 300 DPI
        pix = page.get_pixmap(dpi=300)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        text = pytesseract.image_to_string(img)
        return text.strip(), bool(text.strip())
    except ImportError:
        logger.warning(
            "pytesseract not installed — cannot OCR scanned page. "
            "Install Tesseract + pytesseract for OCR support."
        )
        return "", False
    except Exception as e:
        logger.warning(f"OCR failed on page: {e}")
        return "", False


def _extract_page_text_layout_aware(page: fitz.Page) -> str:
    """
    Extract text from a page using layout-aware block sorting.
    Handles multi-column layouts by sorting text blocks by their
    x-coordinate (column) first, then y-coordinate (reading order).
    """
    blocks = page.get_text("dict", sort=True)["blocks"]

    # Only process text blocks (type 0), skip images (type 1)
    text_blocks = []
    for b in blocks:
        if b.get("type", 0) != 0:
            continue
        # Extract text from block lines and spans
        block_text = ""
        for line in b.get("lines", []):
            line_text = " ".join(
                span["text"] for span in line.get("spans", []) if span.get("text")
            )
            if line_text.strip():
                block_text += line_text.strip() + " "

        if block_text.strip():
            text_blocks.append({
                "text": block_text.strip(),
                "x0": b["bbox"][0],
                "y0": b["bbox"][1],
                "x1": b["bbox"][2],
                "y1": b["bbox"][3],
            })

    if not text_blocks:
        return ""

    # Detect multi-column layout:
    # If blocks have significantly different x-positions, treat as multi-column
    page_width = page.rect.width
    column_threshold = page_width * 0.4  # ~40% of page width

    # Group blocks by column (left vs right)
    left_blocks = []
    right_blocks = []
    for b in text_blocks:
        center_x = (b["x0"] + b["x1"]) / 2
        if center_x < column_threshold:
            left_blocks.append(b)
        else:
            right_blocks.append(b)

    # If both columns have content, process left-to-right, top-to-bottom
    if left_blocks and right_blocks and len(right_blocks) > 2:
        # Sort each column by y-position
        left_blocks.sort(key=lambda b: b["y0"])
        right_blocks.sort(key=lambda b: b["y0"])
        sorted_blocks = left_blocks + right_blocks
    else:
        # Single column — sort by y-position only
        sorted_blocks = sorted(text_blocks, key=lambda b: (b["y0"], b["x0"]))

    # Join all text
    return "\n".join(b["text"] for b in sorted_blocks)


def _detect_tables(page: fitz.Page) -> tuple[bool, list[str]]:
    """Detect tables on a page and extract captions."""
    has_tables = False
    captions = []

    try:
        tables = page.find_tables()
        if tables and len(tables.tables) > 0:
            has_tables = True
    except Exception:
        pass

    # Also look for table/figure captions in the text
    text = page.get_text()
    for match in TABLE_CAPTION_RE.finditer(text):
        captions.append(match.group(0).strip())
        has_tables = True

    return has_tables, captions


def _extract_figure_captions(text: str) -> list[str]:
    """Extract figure captions from page text."""
    return [m.group(0).strip() for m in FIGURE_CAPTION_RE.finditer(text)]


async def ingest_pdf(pdf_path: Path) -> DocumentResult:
    """
    Extract text from a PDF file page-by-page.

    Handles:
    - Normal text PDFs with layout-aware extraction
    - Scanned/image-only PDFs with OCR fallback
    - Multi-column academic layouts
    - Table/figure detection
    - Corrupted/password-protected PDFs
    - Language detection

    Returns:
        DocumentResult with all pages, metadata, and warnings.

    Raises:
        ValueError: For unrecoverable errors (corrupted, password-protected).
    """
    warnings = []

    # ── Open PDF ──────────────────────────────────────────────────────
    try:
        doc = fitz.open(str(pdf_path))
    except fitz.fitz.FileDataError:
        raise ValueError(
            "PDF extraction failed: The file appears to be corrupted or is not a valid PDF."
        )
    except Exception as e:
        if "password" in str(e).lower() or "encrypted" in str(e).lower():
            raise ValueError(
                "PDF extraction failed: This PDF is password-protected. "
                "Please remove the password and try again."
            )
        raise ValueError(f"PDF extraction failed: {e}")

    # Check if password-protected
    if doc.is_encrypted:
        doc.close()
        raise ValueError(
            "PDF extraction failed: This PDF is password-protected. "
            "Please remove the password and try again."
        )

    # ── Extract pages ────────────────────────────────────────────────
    pages: list[PageText] = []
    any_ocr = False

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        page_num = page_idx + 1  # 1-indexed (PDF page, not printed number)

        # Try layout-aware text extraction first
        text = _extract_page_text_layout_aware(page)
        is_ocr = False

        # If no text extracted, try OCR
        if not text.strip():
            ocr_text, ocr_success = _try_ocr(page)
            if ocr_success:
                text = ocr_text
                is_ocr = True
                any_ocr = True
            else:
                text = ""
                warnings.append(
                    f"Page {page_num}: No text could be extracted "
                    "(scanned image without OCR support)"
                )

        # Detect tables
        has_tables, table_captions = _detect_tables(page)

        # Detect figure captions
        figure_captions = _extract_figure_captions(text)

        pages.append(PageText(
            page_number=page_num,
            text=text,
            is_ocr=is_ocr,
            has_tables=has_tables,
            table_captions=table_captions,
            figure_captions=figure_captions,
        ))

    doc.close()

    # ── Language detection ───────────────────────────────────────────
    all_text = " ".join(p.text for p in pages[:3] if p.text)
    detected_lang, is_english = detect_language(all_text)
    is_non_english = not is_english

    if is_non_english:
        warnings.append(
            f"This paper appears to be in '{detected_lang}'. "
            "Analysis results may be less accurate for non-English papers."
        )

    if any_ocr:
        warnings.append(
            "Some pages were processed using OCR (optical character recognition). "
            "Text accuracy may be lower for these pages."
        )

    return DocumentResult(
        pages=pages,
        total_pages=len(pages),
        is_ocr_processed=any_ocr,
        is_non_english=is_non_english,
        detected_language=detected_lang,
        warnings=warnings,
    )
