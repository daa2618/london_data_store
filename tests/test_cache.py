"""Tests for london_data_store.cache module."""

import json
from datetime import UTC, datetime, timedelta

from london_data_store.cache import CatalogueCache

TEST_URL = "https://data.london.gov.uk/api/v2/datasets/export.json"
TEST_DATA = [{"slug": "test-dataset", "tags": ["test"]}]


class TestCatalogueCache:
    def test_cache_miss_returns_none(self, tmp_path):
        cache = CatalogueCache(cache_dir=tmp_path, ttl_seconds=3600)
        assert cache.get(TEST_URL) is None

    def test_put_and_get(self, tmp_path):
        cache = CatalogueCache(cache_dir=tmp_path, ttl_seconds=3600)
        cache.put(TEST_URL, TEST_DATA)
        result = cache.get(TEST_URL)
        assert result == TEST_DATA

    def test_ttl_expired(self, tmp_path):
        cache = CatalogueCache(cache_dir=tmp_path, ttl_seconds=3600)
        cache.put(TEST_URL, TEST_DATA)

        # Fake the fetched_at to be in the past
        meta_path = cache._meta_path(TEST_URL)
        meta = json.loads(meta_path.read_text())
        meta["fetched_at"] = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
        meta_path.write_text(json.dumps(meta))

        assert cache.get(TEST_URL) is None

    def test_ttl_not_expired(self, tmp_path):
        cache = CatalogueCache(cache_dir=tmp_path, ttl_seconds=3600)
        cache.put(TEST_URL, TEST_DATA)
        assert cache.get(TEST_URL) == TEST_DATA

    def test_invalidate_specific_url(self, tmp_path):
        cache = CatalogueCache(cache_dir=tmp_path, ttl_seconds=3600)
        cache.put(TEST_URL, TEST_DATA)
        cache.invalidate(TEST_URL)
        assert cache.get(TEST_URL) is None

    def test_invalidate_all(self, tmp_path):
        cache = CatalogueCache(cache_dir=tmp_path, ttl_seconds=3600)
        cache.put(TEST_URL, TEST_DATA)
        cache.put("https://example.com/other.json", [{"slug": "other"}])
        cache.invalidate()
        assert cache.get(TEST_URL) is None
        assert cache.get("https://example.com/other.json") is None

    def test_corrupt_cache_returns_none(self, tmp_path):
        cache = CatalogueCache(cache_dir=tmp_path, ttl_seconds=3600)
        cache.put(TEST_URL, TEST_DATA)
        # Corrupt the cache file
        cache._cache_path(TEST_URL).write_text("not json{{{")
        assert cache.get(TEST_URL) is None

    def test_corrupt_meta_returns_none(self, tmp_path):
        cache = CatalogueCache(cache_dir=tmp_path, ttl_seconds=3600)
        cache.put(TEST_URL, TEST_DATA)
        cache._meta_path(TEST_URL).write_text("bad meta")
        assert cache.get(TEST_URL) is None

    def test_missing_meta_returns_none(self, tmp_path):
        cache = CatalogueCache(cache_dir=tmp_path, ttl_seconds=3600)
        cache.put(TEST_URL, TEST_DATA)
        cache._meta_path(TEST_URL).unlink()
        assert cache.get(TEST_URL) is None

    def test_cache_dir_created_on_put(self, tmp_path):
        cache_dir = tmp_path / "sub" / "dir"
        cache = CatalogueCache(cache_dir=cache_dir, ttl_seconds=3600)
        cache.put(TEST_URL, TEST_DATA)
        assert cache_dir.exists()

    def test_cache_dir_property(self, tmp_path):
        cache = CatalogueCache(cache_dir=tmp_path)
        assert cache.cache_dir == tmp_path

    def test_default_cache_dir(self):
        cache = CatalogueCache()
        assert "london-data-store" in str(cache.cache_dir)

    def test_different_urls_different_keys(self, tmp_path):
        cache = CatalogueCache(cache_dir=tmp_path, ttl_seconds=3600)
        url2 = "https://example.com/other.json"
        cache.put(TEST_URL, TEST_DATA)
        cache.put(url2, [{"slug": "other"}])
        assert cache.get(TEST_URL) == TEST_DATA
        assert cache.get(url2) == [{"slug": "other"}]

    def test_meta_contains_url_and_timestamp(self, tmp_path):
        cache = CatalogueCache(cache_dir=tmp_path, ttl_seconds=3600)
        cache.put(TEST_URL, TEST_DATA)
        meta = json.loads(cache._meta_path(TEST_URL).read_text())
        assert meta["url"] == TEST_URL
        assert "fetched_at" in meta
        assert meta["ttl_seconds"] == 3600


class TestCacheIntegration:
    def test_api_uses_cache(self, tmp_path):
        """LondonDataStore should use cache when enabled."""
        from london_data_store.api import LondonDataStore

        client = LondonDataStore(cache=True, cache_dir=tmp_path)
        # Pre-populate cache
        cache = CatalogueCache(cache_dir=tmp_path, ttl_seconds=86400)
        cache.put(client.json_url, TEST_DATA)

        result = client.get_data_from_url()
        assert result == TEST_DATA
        client.close()

    def test_api_cache_disabled(self, tmp_path):
        """LondonDataStore with cache=False should not use cache."""
        from london_data_store.api import LondonDataStore

        client = LondonDataStore(cache=False)
        assert client._cache is None
        client.close()

    def test_api_clear_cache(self, tmp_path):
        from london_data_store.api import LondonDataStore

        client = LondonDataStore(cache=True, cache_dir=tmp_path)
        cache = CatalogueCache(cache_dir=tmp_path, ttl_seconds=86400)
        cache.put(client.json_url, TEST_DATA)

        client.clear_cache()
        assert cache.get(client.json_url) is None
        client.close()
