"""
PaperVerify — Structured logging for claim verification verdicts.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from config import LOGS_DIR

# Standard logger for general app logging
logger = logging.getLogger("paperverify")
logger.setLevel(logging.INFO)

# Console handler
_console = logging.StreamHandler()
_console.setFormatter(logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S"
))
logger.addHandler(_console)


def log_verdict(
    session_id: str,
    claim: str,
    claim_type: str,
    chunk_id: str,
    page: int,
    verdict: str,
    reasoning: str = "",
    rewritten_claim: str | None = None,
):
    """
    Log a verification verdict to the session-specific JSONL file.
    Every verdict is logged, including discarded (unsupported) claims.
    """
    log_file = LOGS_DIR / f"verification_{session_id}.jsonl"

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "claim": claim,
        "claim_type": claim_type,
        "chunk_id": chunk_id,
        "page": page,
        "verdict": verdict,
        "reasoning": reasoning,
    }

    if rewritten_claim:
        entry["rewritten_claim"] = rewritten_claim

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # Also log to console
    status_icon = {
        "verified": "✅",
        "partially_supported": "⚠️",
        "unsupported": "❌",
    }.get(verdict, "❓")

    logger.info(
        f"{status_icon} [{verdict}] Page {page} | {claim[:80]}..."
        if len(claim) > 80 else
        f"{status_icon} [{verdict}] Page {page} | {claim}"
    )
