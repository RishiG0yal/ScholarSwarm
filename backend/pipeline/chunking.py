"""
PaperVerify — Stage 2: Semantic Chunking.

Splits document text into chunks of ~300-500 words with:
- Section-header detection for academic papers
- Page-based fallback when no sections found
- References/bibliography exclusion
- Sentence-boundary-aware splitting
"""
import re
import uuid
from models.schemas import PageText, Chunk
from utils.logging_util import logger

# ── Section header patterns ──────────────────────────────────────────
SECTION_HEADERS = [
    r"^#{1,3}\s+",
    r"^(?:\d+\.?\s+)?(Abstract|Introduction|Background|Related\s+Work|"
    r"Literature\s+Review|Methodology|Methods?|Materials?\s+and\s+Methods?|"
    r"Experimental?\s+(?:Setup|Design|Methods?)|Results?(?:\s+and\s+Discussion)?|"
    r"Discussion|Analysis|Findings|Conclusion|Conclusions|"
    r"Summary|Acknowledgments?|Funding|Declarations?|"
    r"Data\s+Availability|Author\s+Contributions?)"
    r"\s*$",
]
SECTION_RE = re.compile("|".join(SECTION_HEADERS), re.IGNORECASE | re.MULTILINE)

# ── References detection ─────────────────────────────────────────────
REFERENCES_RE = re.compile(
    r"^(?:\d+\.?\s+)?(References|Bibliography|Works?\s+Cited|Literature\s+Cited)\s*$",
    re.IGNORECASE | re.MULTILINE,
)

# ── Sentence boundary ────────────────────────────────────────────────
SENTENCE_END_RE = re.compile(
    r'(?<=[.!?])\s+(?=[A-Z"\(\[])|'   # Standard sentence end
    r'(?<=[.!?])\s*\n',                 # Sentence end at line break
    re.MULTILINE,
)


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences, trying not to break mid-sentence."""
    if not text.strip():
        return []

    # Split on sentence boundaries
    sentences = SENTENCE_END_RE.split(text)

    # Clean up
    result = []
    for s in sentences:
        s = s.strip()
        if s:
            result.append(s)

    # If regex produced no splits, fall back to simple period splitting
    if len(result) <= 1 and len(text.split()) > 50:
        parts = re.split(r'(?<=[.!?])\s+', text)
        result = [p.strip() for p in parts if p.strip()]

    return result if result else [text.strip()]


def _detect_sections(full_text: str) -> list[tuple[str, str]]:
    """
    Detect section headers and split text into (section_name, section_text) pairs.
    Returns empty list if no clear section headers found.
    """
    matches = list(SECTION_RE.finditer(full_text))

    if len(matches) < 2:
        return []

    sections = []
    for i, match in enumerate(matches):
        section_name = match.group(0).strip().lstrip("# ").strip()
        # Clean up numbering
        section_name = re.sub(r"^\d+\.?\s*", "", section_name).strip()

        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        section_text = full_text[start:end].strip()

        if section_text:
            sections.append((section_name, section_text))

    return sections


def _is_references_section(section_name: str) -> bool:
    """Check if a section is the references/bibliography."""
    return bool(REFERENCES_RE.match(section_name))


def _chunk_text(
    text: str,
    page_number: int,
    section_guess: str,
    session_id: str,
    chunk_idx_start: int,
    min_words: int = 300,
    max_words: int = 500,
) -> tuple[list[Chunk], int]:
    """
    Split text into chunks of min_words to max_words, never cutting mid-sentence.
    Returns (chunks, next_chunk_idx).
    """
    sentences = _split_sentences(text)
    if not sentences:
        return [], chunk_idx_start

    chunks = []
    current_sentences = []
    current_word_count = 0
    chunk_idx = chunk_idx_start

    for sentence in sentences:
        word_count = len(sentence.split())

        # If adding this sentence would exceed max, finalize current chunk
        if current_word_count + word_count > max_words and current_sentences:
            chunk_text = " ".join(current_sentences)
            chunks.append(Chunk(
                chunk_id=f"{session_id}_p{page_number}_c{chunk_idx}",
                text=chunk_text,
                page_number=page_number,
                section_guess=section_guess,
                word_count=len(chunk_text.split()),
            ))
            chunk_idx += 1
            current_sentences = []
            current_word_count = 0

        current_sentences.append(sentence)
        current_word_count += word_count

    # Don't forget the last chunk
    if current_sentences:
        chunk_text = " ".join(current_sentences)
        chunks.append(Chunk(
            chunk_id=f"{session_id}_p{page_number}_c{chunk_idx}",
            text=chunk_text,
            page_number=page_number,
            section_guess=section_guess,
            word_count=len(chunk_text.split()),
        ))
        chunk_idx += 1

    return chunks, chunk_idx


async def chunk_document(
    pages: list[PageText],
    session_id: str,
    min_words: int = 300,
    max_words: int = 500,
) -> list[Chunk]:
    """
    Split document pages into semantic chunks.

    Strategy:
    1. Try section-header detection first
    2. Fall back to page-based chunking if no sections found
    3. Always exclude references/bibliography section
    4. Never cut mid-sentence

    Returns:
        List of Chunk objects with metadata.
    """
    # Concatenate all page text for section detection
    full_text = "\n\n".join(
        f"[PAGE {p.page_number}]\n{p.text}"
        for p in pages if p.text.strip()
    )

    # Try section-based chunking
    sections = _detect_sections(full_text)

    all_chunks: list[Chunk] = []
    chunk_idx = 0

    if sections:
        logger.info(f"Found {len(sections)} sections — using section-based chunking")

        for section_name, section_text in sections:
            # Skip references
            if _is_references_section(section_name):
                logger.info(f"Skipping references section: '{section_name}'")
                continue

            # Determine which page this section starts on
            # Look for [PAGE N] markers
            page_match = re.search(r"\[PAGE (\d+)\]", section_text)
            page_num = int(page_match.group(1)) if page_match else 1

            # Clean page markers from text
            clean_text = re.sub(r"\[PAGE \d+\]\n?", "", section_text).strip()

            if not clean_text:
                continue

            new_chunks, chunk_idx = _chunk_text(
                text=clean_text,
                page_number=page_num,
                section_guess=section_name,
                session_id=session_id,
                chunk_idx_start=chunk_idx,
                min_words=min_words,
                max_words=max_words,
            )
            all_chunks.extend(new_chunks)
    else:
        logger.info("No clear section headers — using page-based chunking")

        for page in pages:
            if not page.text.strip():
                continue

            # Check if this page starts the references
            if REFERENCES_RE.search(page.text[:200]):
                logger.info(f"References detected on page {page.page_number} — stopping")
                break

            new_chunks, chunk_idx = _chunk_text(
                text=page.text,
                page_number=page.page_number,
                section_guess="Unknown",
                session_id=session_id,
                chunk_idx_start=chunk_idx,
                min_words=min_words,
                max_words=max_words,
            )
            all_chunks.extend(new_chunks)

    logger.info(f"Created {len(all_chunks)} chunks from {len(pages)} pages")
    return all_chunks
