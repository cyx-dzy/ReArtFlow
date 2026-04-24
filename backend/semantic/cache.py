"""Simple caching layer for LLM responses.

- Primary cache: Redis (connection string from ``REDIS_URL`` env var).
- Fallback: local JSON file stored under ``.cache/llm_responses.json``.

Cache key is a SHA‑256 hash of the request payload (code + model + provider).
TTL defaults to 24 h (86400 s)."""

import os
import json
import hashlib
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helper to compute a deterministic key (mirrors llm_client._build_key)
# ---------------------------------------------------------------------------
def _make_key(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

# ---------------------------------------------------------------------------
# Redis client – lazily instantiated; if connection fails we fall back.
# ---------------------------------------------------------------------------
_redis_client = None

def _get_redis():
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return None
    try:
        import redis
        _redis_client = redis.from_url(redis_url)
        # Test connection
        _redis_client.ping()
        return _redis_client
    except Exception as e:  # pragma: no cover – connection failures are environment‑specific
        logger.warning("Redis unavailable (%s); using file fallback", e)
        return None

# ---------------------------------------------------------------------------
# File‑based fallback cache location
# ---------------------------------------------------------------------------
_CACHE_DIR = Path('.cache')
_CACHE_DIR.mkdir(exist_ok=True)
_CACHE_FILE = _CACHE_DIR / 'llm_responses.json'

def _load_file_cache() -> dict:
    if _CACHE_FILE.is_file():
        try:
            with open(_CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error("Failed to load cache file %s: %s", _CACHE_FILE, e)
    return {}

def _save_file_cache(cache: dict) -> None:
    try:
        with open(_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error("Failed to write cache file %s: %s", _CACHE_FILE, e)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def get_cached(key: str) -> Optional[dict]:
    """Return cached response dict if present, else ``None``.
    Looks in Redis first, then falls back to file cache.
    """
    r = _get_redis()
    if r:
        try:
            raw = r.get(key)
            if raw:
                return json.loads(raw)
        except Exception as e:
            logger.warning("Redis get error for key %s: %s", key, e)
    # File fallback
    cache = _load_file_cache()
    return cache.get(key)

def set_cached(key: str, value: dict, ttl: int = 86400) -> None:
    """Store *value* under *key* with optional TTL (seconds)."""
    r = _get_redis()
    serialized = json.dumps(value, ensure_ascii=False)
    if r:
        try:
            r.set(key, serialized, ex=ttl)
            return
        except Exception as e:
            logger.warning("Redis set error for key %s: %s", key, e)
    # File fallback – load existing, update, and write back
    cache = _load_file_cache()
    cache[key] = value
    _save_file_cache(cache)
