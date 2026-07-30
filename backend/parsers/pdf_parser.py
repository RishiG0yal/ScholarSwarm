"""
PDF Parser — Extracts text from PDF files with page-level coordinate mapping.
Uses PyPDF2 to extract text page by page and splits into paragraphs.
"""

import os
import logging
from PyPDF2 import PdfReader
from backend.models.schemas import TextChunk, ParsedDocument

logger = logging.getLogger("rag_pipeline.parsers.pdf")


def parse_pdf(file_path: str, file_id: str) -> ParsedDocument:
    """
    Parse a PDF file and return structured text chunks with coordinates.

    Args:
        file_path: Absolute path to the PDF file.
        file_id: Unique identifier for this file upload.

    Returns:
        ParsedDocument with text chunks mapped to [Page X, Paragraph Y].
    """
    filename = os.path.basename(file_path)
    logger.info(f"Parsing PDF: {filename}")

    reader = PdfReader(file_path)
    total_pages = len(reader.pages)
    chunks: list[TextChunk] = []
    chunk_counter = 0

    for page_idx, page in enumerate(reader.pages):
        page_num = page_idx + 1
        raw_text = page.extract_text() or ""

        if not raw_text.strip():
            logger.debug(f"  Page {page_num}: empty, skipping")
            continue

        # Split into paragraphs by double newlines or significant whitespace
        paragraphs = _split_into_paragraphs(raw_text)

        for para_idx, para_text in enumerate(paragraphs):
            if not para_text.strip():
                continue
            chunk_counter += 1
            chunks.append(
                TextChunk(
                    text=para_text.strip(),
                    page_number=page_num,
                    paragraph_number=para_idx + 1,
                    source_file=filename,
                    chunk_id=f"{file_id}_p{page_num}_para{para_idx + 1}",
                )
            )

    logger.info(
        f"  Extracted {len(chunks)} chunks from {total_pages} pages"
    )

    return ParsedDocument(
        file_id=file_id,
        filename=filename,
        file_type="pdf",
        total_pages=total_pages,
        total_chunks=len(chunks),
        chunks=chunks,
    )


def _split_into_paragraphs(text: str) -> list[str]:
    """
    Split raw text into meaningful paragraphs.
    Handles double newlines, and falls back to single newlines
    if no double newlines are found.
    """
    # Try splitting on double newlines first
    paragraphs = text.split("\n\n")

    if len(paragraphs) <= 1:
        # Fallback: split on single newlines but merge short lines
        lines = text.split("\n")
        paragraphs = []
        current = []
        for line in lines:
            stripped = line.strip()
            if not stripped and current:
                paragraphs.append(" ".join(current))
                current = []
            elif stripped:
                current.append(stripped)
        if current:
            paragraphs.append(" ".join(current))

    return [p for p in paragraphs if p.strip()]
