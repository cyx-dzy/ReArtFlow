"""Simple caching layer for LLM responses."""

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_redis_client = None
_CACHE_DIR = Path('.cache')
_CACHE_DIR.mkdir(exist_ok=True)
_CACHE_FILE = _CACHE_DIR / 'llm_responses.json'


def _make_key(raw: str) -> str:
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def _get_redis():
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    redis_url = os.getenv('REDIS_URL')
    if not redis_url:
        return None
    try:
        import redis
        _redis_client = redis.from_url(redis_url)
        _redis_client.ping()
        return _redis_client
    except Exception as exc:  # pragma: no cover
        logger.warning('Redis unavailable (%s); using file fallback', exc)
        return None


def _load_file_cache() -> dict:
    if _CACHE_FILE.is_file():
        try:
            with open(_CACHE_FILE, 'r', encoding='utf-8') as handle:
                return json.load(handle)
        except Exception as exc:
            logger.error('Failed to load cache file %s: %s', _CACHE_FILE, exc)
    return {}


def _save_file_cache(cache: dict) -> None:
    try:
        with open(_CACHE_FILE, 'w', encoding='utf-8') as handle:
            json.dump(cache, handle, ensure_ascii=False, indent=2)
    except Exception as exc:
        logger.error('Failed to write cache file %s: %s', _CACHE_FILE, exc)


def get_cached(key: str) -> Optional[dict]:
    redis_client = _get_redis()
    if redis_client:
        try:
            raw = redis_client.get(key)
            if raw:
                return json.loads(raw)
        except Exception as exc:
            logger.warning('Redis get error for key %s: %s', key, exc)
    return _load_file_cache().get(key)


def set_cached(key: str, value: dict, ttl: int = 86400) -> None:
    redis_client = _get_redis()
    serialized = json.dumps(value, ensure_ascii=False)
    if redis_client:
        try:
            redis_client.set(key, serialized, ex=ttl)
            return
        except Exception as exc:
            logger.warning('Redis set error for key %s: %s', key, exc)
    cache = _load_file_cache()
    cache[key] = value
    _save_file_cache(cache)


class SemanticCache:
    def get(self, payload: Any) -> Optional[dict]:
        key = _make_key(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return get_cached(key)

    def set(self, payload: Any, value: dict, ttl: int = 86400) -> None:
        key = _make_key(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        set_cached(key, value, ttl=ttl)
