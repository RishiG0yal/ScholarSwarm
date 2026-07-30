import re

CITATION_PATTERNS = [
    r'\[\d+\]',
    r'\[\d+(?:,\s*\d+)+\]',
    r'\[\d+\s*[-–]\s*\d+\]',
    r'\([A-Z][a-z]+(?:\s+et\s+al\.?)?,\s*\d{4}\)',
    r'\([A-Z][a-z]+\s+et\s+al\.,?\s*\d{4}\)',
    r'\([A-Z][a-z]+\s+&\s+[A-Z][a-z]+,\s*\d{4}\)',
    r'\([A-Z][a-z]+\s+and\s+[A-Z][a-z]+,\s*\d{4}\)',
    r'[A-Z][a-z]+\s+et\s+al\.\s+\(\d{4}\)',
    r'[A-Z][a-z]+\s+\(\d{4}\)',
]


def extract_citations(text: str) -> list:
    found = set()
    for pattern in CITATION_PATTERNS:
        for match in re.findall(pattern, text):
            found.add(match.strip())
    found = {c for c in found if len(c) > 3}
    return sorted(list(found))[:20]
