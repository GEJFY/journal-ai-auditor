"""In-memory TTL cache for AI agent responses.

Provides a simple thread-safe LRU cache with time-based expiration
to reduce redundant LLM calls for identical queries.
"""

import hashlib
import json
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any


@dataclass
class CacheEntry:
    """Single cache entry with value and expiration timestamp."""

    value: Any
    expires_at: float


class TTLCache:
    """Thread-safe LRU cache with TTL expiration.

    Args:
        max_size: Maximum number of entries.
        ttl_seconds: Time-to-live for each entry.
    """

    def __init__(self, max_size: int = 256, ttl_seconds: int = 300) -> None:
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    @staticmethod
    def _make_key(*args: Any, **kwargs: Any) -> str:
        """Generate a deterministic cache key from arguments."""
        raw = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    def get(self, key: str) -> Any | None:
        """Retrieve a value if it exists and hasn't expired."""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None
            if time.time() > entry.expires_at:
                del self._cache[key]
                self._misses += 1
                return None
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._hits += 1
            return entry.value

    def set(self, key: str, value: Any) -> None:
        """Store a value with TTL expiration."""
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = CacheEntry(
                value=value,
                expires_at=time.time() + self._ttl,
            )
            # Evict oldest if over max size
            while len(self._cache) > self._max_size:
                self._cache.popitem(last=False)

    def invalidate(self, key: str) -> None:
        """Remove a specific entry."""
        with self._lock:
            self._cache.pop(key, None)

    def clear(self) -> None:
        """Remove all entries."""
        with self._lock:
            self._cache.clear()

    @property
    def stats(self) -> dict[str, int]:
        """Return cache hit/miss statistics."""
        return {
            "hits": self._hits,
            "misses": self._misses,
            "size": len(self._cache),
            "max_size": self._max_size,
        }


# Global cache instance for agent responses
agent_cache = TTLCache(max_size=256, ttl_seconds=300)
