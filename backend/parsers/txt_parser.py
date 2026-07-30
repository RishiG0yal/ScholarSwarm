"""
TXT Parser — Extracts text from plain text files with line-based coordinate mapping.
Groups lines into paragraphs separated by blank lines.
"""

import os
import logging
from backend.models.schemas import TextChunk, ParsedDocument

logger = logging.getLogger("rag_pipeline.parsers.txt")

# Approximate lines per "page" for coordinate mapping
_LINES_PER_PAGE = 40


def parse_txt(file_path: str, file_id: str) -> ParsedDocument:
    """
    Parse a TXT file and return structured text chunks with coordinates.

    Args:
        file_path: Absolute path to the TXT file.
        file_id: Unique identifier for this file upload.

    Returns:
        ParsedDocument with text chunks mapped to estimated [Page X, Paragraph Y].
    """
    filename = os.path.basename(file_path)
    logger.info(f"Parsing TXT: {filename}")

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    # Split into paragraphs by double newlines
    raw_paragraphs = content.split("\n\n")
    chunks: list[TextChunk] = []
    total_lines_so_far = 0

    for para_text in raw_paragraphs:
        stripped = para_text.strip()
        if not stripped:
            total_lines_so_far += 1
            continue

        # Count lines in this paragraph for page estimation
        para_lines = para_text.count("\n") + 1
        page_num = (total_lines_so_far // _LINES_PER_PAGE) + 1
        para_on_page = len(
            [c for c in chunks if c.page_number == page_num]
        ) + 1

        chunks.append(
            TextChunk(
                text=stripped,
                page_number=page_num,
                paragraph_number=para_on_page,
                source_file=filename,
                chunk_id=f"{file_id}_p{page_num}_para{para_on_page}",
            )
        )

        total_lines_so_far += para_lines + 1  # +1 for the blank line separator

    total_pages = (total_lines_so_far // _LINES_PER_PAGE) + 1
    logger.info(f"  Extracted {len(chunks)} chunks (~{total_pages} estimated pages)")

    return ParsedDocument(
        file_id=file_id,
        filename=filename,
        file_type="txt",
        total_pages=total_pages,
        total_chunks=len(chunks),
        chunks=chunks,
    )
