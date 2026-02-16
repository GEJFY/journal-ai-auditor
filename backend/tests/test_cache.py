"""Tests for TTLCache module."""

import time
from unittest.mock import patch

from app.core.cache import CacheEntry, TTLCache, agent_cache


class TestCacheEntry:
    def test_fields(self):
        entry = CacheEntry(value="hello", expires_at=123.0)
        assert entry.value == "hello"
        assert entry.expires_at == 123.0


class TestTTLCacheMakeKey:
    def test_deterministic(self):
        k1 = TTLCache._make_key("q", fiscal_year=2024)
        k2 = TTLCache._make_key("q", fiscal_year=2024)
        assert k1 == k2

    def test_different_args_different_keys(self):
        k1 = TTLCache._make_key("q1")
        k2 = TTLCache._make_key("q2")
        assert k1 != k2

    def test_key_length(self):
        key = TTLCache._make_key("question", context={"a": 1})
        assert len(key) == 32


class TestTTLCacheGetSet:
    def test_set_and_get(self):
        cache = TTLCache(max_size=10, ttl_seconds=60)
        cache.set("k1", {"answer": "yes"})
        assert cache.get("k1") == {"answer": "yes"}

    def test_get_miss(self):
        cache = TTLCache(max_size=10, ttl_seconds=60)
        assert cache.get("nonexistent") is None

    def test_expired_entry_returns_none(self):
        cache = TTLCache(max_size=10, ttl_seconds=1)
        cache.set("k1", "value")

        with patch("app.core.cache.time") as mock_time:
            # set 時点
            mock_time.time.return_value = time.time() + 100
            assert cache.get("k1") is None

    def test_lru_eviction(self):
        cache = TTLCache(max_size=2, ttl_seconds=60)
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        cache.set("k3", "v3")  # k1 が追い出される
        assert cache.get("k1") is None
        assert cache.get("k2") == "v2"
        assert cache.get("k3") == "v3"

    def test_overwrite_existing_key(self):
        cache = TTLCache(max_size=10, ttl_seconds=60)
        cache.set("k1", "old")
        cache.set("k1", "new")
        assert cache.get("k1") == "new"

    def test_move_to_end_on_access(self):
        cache = TTLCache(max_size=2, ttl_seconds=60)
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        cache.get("k1")  # k1 にアクセス → LRU順序が変わる
        cache.set("k3", "v3")  # k2 が追い出される（k1ではなく）
        assert cache.get("k1") == "v1"
        assert cache.get("k2") is None
        assert cache.get("k3") == "v3"


class TestTTLCacheInvalidate:
    def test_invalidate_existing(self):
        cache = TTLCache(max_size=10, ttl_seconds=60)
        cache.set("k1", "v1")
        cache.invalidate("k1")
        assert cache.get("k1") is None

    def test_invalidate_nonexistent(self):
        cache = TTLCache(max_size=10, ttl_seconds=60)
        cache.invalidate("nonexistent")  # エラーにならない


class TestTTLCacheClear:
    def test_clear(self):
        cache = TTLCache(max_size=10, ttl_seconds=60)
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        cache.clear()
        assert cache.get("k1") is None
        assert cache.get("k2") is None
        assert cache.stats["size"] == 0


class TestTTLCacheStats:
    def test_initial_stats(self):
        cache = TTLCache(max_size=128, ttl_seconds=60)
        stats = cache.stats
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["size"] == 0
        assert stats["max_size"] == 128

    def test_hit_miss_tracking(self):
        cache = TTLCache(max_size=10, ttl_seconds=60)
        cache.set("k1", "v1")
        cache.get("k1")  # hit
        cache.get("k2")  # miss
        cache.get("k3")  # miss
        stats = cache.stats
        assert stats["hits"] == 1
        assert stats["misses"] == 2
        assert stats["size"] == 1


class TestGlobalAgentCache:
    def test_global_instance_exists(self):
        assert agent_cache is not None
        assert isinstance(agent_cache, TTLCache)
        assert agent_cache._max_size == 256
        assert agent_cache._ttl == 300
