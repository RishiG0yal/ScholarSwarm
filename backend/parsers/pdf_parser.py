import fitz
import re


def extract_text_from_pdf(file_bytes: bytes) -> dict:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages = {}
    full_text = ""
    total_pages = len(doc)

    for i in range(total_pages):
        page = doc[i]
        blocks = page.get_text("blocks", sort=True)
        page_text = ""
        for block in blocks:
            if block[6] == 0:
                text = block[4].strip()
                if text:
                    page_text += text + "\n"
        pages[i + 1] = page_text
        full_text += page_text + "\n"

    page1_lines = [l.strip() for l in pages.get(1, "").splitlines() if l.strip()]
    title = _extract_title(page1_lines)
    authors = _extract_authors(page1_lines, title)
    doc.close()

    return {
        "pages": pages,
        "full_text": full_text.strip(),
        "title": title,
        "authors": authors,
        "total_pages": total_pages,
        "file_type": "pdf",
    }


def _extract_title(lines: list) -> str:
    if not lines:
        return "Unknown Title"

    candidates = []
    for line in lines[:12]:
        stripped = line.strip()
        if len(stripped) < 5:
            continue
        # Skip lines that look like author lists (names with commas/&)
        if _looks_like_authors(stripped):
            continue
        # Skip institution lines
        if _looks_like_institution(stripped):
            continue
        # Skip abstract header
        if stripped.upper() in ("ABSTRACT", "INTRODUCTION", "SUMMARY"):
            continue
        # Skip URLs, DOIs, emails
        if any(x in stripped.lower() for x in ["http", "doi:", "@", "arxiv", "©", "copyright"]):
            continue
        candidates.append(stripped)

    if not candidates:
        return lines[0] if lines else "Unknown Title"

    # Prefer ALL CAPS lines (common for paper titles)
    all_caps = [c for c in candidates[:6] if c.isupper() and len(c) > 5]
    if all_caps:
        return all_caps[0]

    # Prefer Title Case lines in first 5 candidates
    title_case = [c for c in candidates[:5] if _is_title_case(c) and len(c) > 10]
    if title_case:
        return title_case[0]

    # Fall back to first meaningful candidate
    return candidates[0]


def _extract_authors(lines: list, title: str) -> str:
    title_lower = title.lower()
    for line in lines[:12]:
        stripped = line.strip()
        if stripped.lower() == title_lower:
            continue
        if len(stripped) < 5:
            continue
        if _looks_like_authors(stripped):
            return stripped
        # Author lines often have multiple capitalized words with commas
        if "," in stripped and len(stripped) < 250:
            words = stripped.split()
            cap_words = sum(1 for w in words if w and w[0].isupper())
            if cap_words >= 2 and len(words) >= 2:
                if not _looks_like_institution(stripped):
                    return stripped
    return "Unknown Authors"


def _looks_like_authors(text: str) -> bool:
    # Author patterns: "Name, Name & Name" or "Name1, Name2, Name3"
    if re.search(r'[A-Z][a-z]+\s+[A-Z][a-z]+,\s+[A-Z]', text):
        return True
    if re.search(r'[A-Z][a-z]+\s+[A-Z][a-z]+\s+&\s+[A-Z]', text):
        return True
    if re.search(r'[A-Z][a-z]+\s+[A-Z][a-z]+,\s+[A-Z][a-z]+\s+[A-Z][a-z]+', text):
        return True
    return False


def _looks_like_institution(text: str) -> bool:
    keywords = ["university", "institute", "laboratory", "lab ", "department",
                 "college", "school", "research", "corporation", "inc.", "ltd",
                 "carnegie", "stanford", "mit ", "google", "microsoft", "amazon",
                 "meta ", "apple ", "openai", "deepmind"]
    lower = text.lower()
    return any(kw in lower for kw in keywords)


def _is_title_case(text: str) -> bool:
    words = text.split()
    if len(words) < 2:
        return False
    cap_words = sum(1 for w in words if w and w[0].isupper())
    return cap_words / len(words) >= 0.6
