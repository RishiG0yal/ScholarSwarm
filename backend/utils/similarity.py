import re
import math
from collections import Counter

STOPWORDS = {
    "the", "a", "an", "is", "was", "are", "were", "this", "that", "of", "in",
    "to", "and", "or", "for", "with", "on", "at", "by", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could", "should",
    "it", "its", "we", "our", "they", "their", "from", "as", "which", "that",
    "but", "not", "also", "more", "can", "may", "such", "into", "than", "after",
}

K1 = 1.5
B = 0.75


def bm25_score(query: str, document: str, avg_doc_len: float = 500.0) -> float:
    query_tokens = _tokenize(query)
    doc_tokens = _tokenize(document)
    doc_len = len(doc_tokens)

    if not query_tokens or not doc_tokens:
        return 0.0

    doc_freq = Counter(doc_tokens)
    score = 0.0

    for term in query_tokens:
        tf = doc_freq.get(term, 0)
        if tf == 0:
            continue
        numerator = tf * (K1 + 1)
        denominator = tf + K1 * (1 - B + B * doc_len / avg_doc_len)
        score += numerator / denominator

    return round(score, 4)


def tfidf_similarity(text1: str, text2: str) -> float:
    tf1 = _term_freq(_tokenize(text1))
    tf2 = _term_freq(_tokenize(text2))

    if not tf1 or not tf2:
        return 0.0

    vocab = set(tf1) | set(tf2)
    dot = sum(tf1.get(w, 0.0) * tf2.get(w, 0.0) for w in vocab)
    mag1 = math.sqrt(sum(v * v for v in tf1.values()))
    mag2 = math.sqrt(sum(v * v for v in tf2.values()))

    if mag1 == 0 or mag2 == 0:
        return 0.0

    return round(min(dot / (mag1 * mag2), 1.0), 3)


def retrieve_top_chunks(question: str, page_texts: dict, top_k: int = 4) -> list:
    """
    BM25 retrieval over page texts.
    Returns list of (page_num, text, score) sorted by page number for context continuity.
    Normalizes page keys to int to avoid type mismatch bugs.
    """
    if not page_texts:
        return []

    # Normalize keys to int
    normalized = {int(k): v for k, v in page_texts.items()}
    avg_len = sum(len(_tokenize(t)) for t in normalized.values()) / len(normalized)

    scored = []
    for page_num, text in normalized.items():
        score = bm25_score(question, text, avg_len)
        scored.append((page_num, text, score))

    scored.sort(key=lambda x: x[2], reverse=True)
    top = list(scored[:top_k])
    top_page_nums = {p for p, _, _ in top}

    # Include neighboring pages for context continuity
    top_by_score = sorted(top, key=lambda x: x[2], reverse=True)
    if top_by_score:
        best_page = top_by_score[0][0]
        for neighbor in [best_page - 1, best_page + 1]:
            if neighbor in normalized and neighbor not in top_page_nums:
                top.append((neighbor, normalized[neighbor], top_by_score[0][2] * 0.5))
                top_page_nums.add(neighbor)

    # Sort by page number for readable context
    top.sort(key=lambda x: x[0])
    return top


def blend_confidence(llm_confidence: float, similarity_score: float) -> float:
    return round(llm_confidence * 0.65 + similarity_score * 0.35, 2)


def _tokenize(text: str) -> list:
    tokens = re.findall(r'\b[a-z]{2,}\b', text.lower())
    return [t for t in tokens if t not in STOPWORDS]


def _term_freq(tokens: list) -> dict:
    freq = Counter(tokens)
    total = len(tokens) or 1
    return {k: v / total for k, v in freq.items()}
