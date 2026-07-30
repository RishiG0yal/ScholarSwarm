import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

_cache: dict = {}
EXPIRY_HOURS = 2


def store_result(data: dict) -> str:
    for _ in range(5):
        result_id = uuid.uuid4().hex[:8]
        if result_id not in _cache:
            break
    _cache[result_id] = {
        "data": data,
        "created_at": datetime.now(timezone.utc),
    }
    _cleanup_expired()
    return result_id


def get_result(result_id: str) -> Optional[dict]:
    entry = _cache.get(result_id)
    if not entry:
        return None
    if datetime.now(timezone.utc) - entry["created_at"] > timedelta(hours=EXPIRY_HOURS):
        del _cache[result_id]
        return None
    return entry["data"]


def _cleanup_expired():
    now = datetime.now(timezone.utc)
    expired = [
        k for k, v in _cache.items()
        if now - v["created_at"] > timedelta(hours=EXPIRY_HOURS)
    ]
    for k in expired:
        del _cache[k]
