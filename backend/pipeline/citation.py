"""
PaperVerify — Stage 6: Citation Formatting.

Formats verified claims with page-level citations and short exact quotes.
"""
import re
from models.schemas import VerifiedClaim
from config import MAX_QUOTE_WORDS
from utils.logging_util import logger


def _truncate_quote(quote: str, max_words: int = MAX_QUOTE_WORDS) -> str:
    """Ensure a quote is under the max word limit."""
    words = quote.split()
    if len(words) <= max_words:
        return quote
    return " ".join(words[:max_words]) + "..."


def format_citations(claims: list[VerifiedClaim]) -> list[VerifiedClaim]:
    """
    Format citations for all verified claims.

    Each claim gets:
    - A page reference: (Page N)
    - A short exact quote (≤15 words) from the source

    The source_quote field is cleaned and truncated.
    Claims are returned with properly formatted citation data.
    """
    formatted = []

    for claim in claims:
        # Clean and truncate the source quote
        quote = claim.source_quote.strip()
        quote = re.sub(r'\s+', ' ', quote)  # Normalize whitespace
        quote = quote.strip('"\'')  # Remove wrapping quotes
        quote = _truncate_quote(quote)

        # Update the claim with the formatted quote
        formatted_claim = claim.model_copy(update={
            "source_quote": quote,
        })
        formatted.append(formatted_claim)

    logger.info(f"Formatted citations for {len(formatted)} claims")
    return formatted
