"""
Recommendation Cache
====================
In-memory TTL cache for RAG vendor recommendations.
Prevents repeated LLM calls for the same (item, quantity) during demos.

Key: (item_id_str, quantity_bracket) where quantity_bracket = round(qty/10)*10
TTL: VENDOR_REC_CACHE_TTL_MINUTES (default 15 minutes)
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import uuid

from app.core.config import settings
from app.schemas.domain import RAGVendorRecommendation

logger = logging.getLogger(__name__)

# Thread-safe for single-process FastAPI (no multiprocessing concerns for demo)
_cache: Dict[Tuple[str, int], Tuple[datetime, List[RAGVendorRecommendation]]] = {}


def _make_key(item_id: uuid.UUID, quantity: float) -> Tuple[str, int]:
    """
    Cache key: (item_id_str, quantity_bracket)
    quantity_bracket groups similar quantities together (increments of 10)
    to avoid cache misses for qty=30 vs qty=31.
    """
    bracket = round(quantity / 10) * 10
    return (str(item_id), bracket)


def get_cached(item_id: uuid.UUID, quantity: float) -> Optional[List[RAGVendorRecommendation]]:
    """
    Returns cached recommendations if they exist and haven't expired.
    Returns None on cache miss or TTL expiry.
    """
    key = _make_key(item_id, quantity)
    entry = _cache.get(key)
    if not entry:
        return None

    cached_at, recs = entry
    ttl = timedelta(minutes=settings.VENDOR_REC_CACHE_TTL_MINUTES)
    if datetime.utcnow() - cached_at > ttl:
        del _cache[key]
        logger.debug(f"[RecCache] Cache expired for key {key}")
        return None

    logger.debug(f"[RecCache] Cache HIT for item={item_id}, qty_bracket={key[1]}")
    return recs


def set_cached(item_id: uuid.UUID, quantity: float, recs: List[RAGVendorRecommendation]) -> None:
    """Store recommendations in cache with current timestamp."""
    key = _make_key(item_id, quantity)
    _cache[key] = (datetime.utcnow(), recs)
    logger.debug(f"[RecCache] Cached {len(recs)} recommendations for key {key}")


def invalidate(item_id: uuid.UUID) -> None:
    """Invalidate all cached entries for a given item (call when data changes)."""
    keys_to_remove = [k for k in _cache.keys() if k[0] == str(item_id)]
    for key in keys_to_remove:
        del _cache[key]
    if keys_to_remove:
        logger.debug(f"[RecCache] Invalidated {len(keys_to_remove)} cache entries for item {item_id}")


def clear_all() -> None:
    """Clear the entire cache (useful for testing or after re-seeding)."""
    _cache.clear()
    logger.info("[RecCache] Cache cleared.")
