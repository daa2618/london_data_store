"""Tests for london_data_store.async_client module."""

import pytest

from london_data_store.async_client import AsyncLondonDataStore
from london_data_store.exceptions import DatasetNotFoundError
from london_data_store.models import Dataset

pytestmark = pytest.mark.asyncio


@pytest.fixture
def async_client(sample_catalogue):
    """Return an AsyncLondonDataStore with pre-loaded data."""
    client = AsyncLondonDataStore(cache=False)
    client._raw_response_json = sample_catalogue
    return client


class TestAsyncInit:
    async def test_default_url(self):
        client = AsyncLondonDataStore(cache=False)
        assert "data.london.gov.uk" in client.json_url
        assert "/api/v2/" in client.json_url

    async def test_context_manager(self):
        async with AsyncLondonDataStore(cache=False) as client:
            assert client is not None

    async def test_base_url(self):
        client = AsyncLondonDataStore(cache=False)
        assert client.base_url == "https://data.london.gov.uk"


class TestAsyncGetAllSlugs:
    async def test_returns_sorted(self, async_client):
        slugs = await async_client.get_all_slugs()
        assert slugs == sorted(slugs)
        assert "population-projections" in slugs

    async def test_no_duplicates(self, async_client):
        slugs = await async_client.get_all_slugs()
        assert len(slugs) == len(set(slugs))


class TestAsyncSearch:
    async def test_returns_scored_tuples(self, async_client):
        results = await async_client.search("population")
        assert isinstance(results, list)
        assert all(isinstance(r, tuple) for r in results)

    async def test_sorted_descending(self, async_client):
        results = await async_client.search("cycling")
        scores = [r[1] for r in results]
        assert scores == sorted(scores, reverse=True)

    async def test_best_match_first(self, async_client):
        results = await async_client.search("cycling")
        assert results[0][0] == "cycling-infrastructure"

    async def test_limit(self, async_client):
        results = await async_client.search("a", limit=2)
        assert len(results) <= 2


class TestAsyncGetDataset:
    async def test_returns_dataset(self, async_client):
        ds = await async_client.get_dataset("population-projections")
        assert isinstance(ds, Dataset)
        assert ds.slug == "population-projections"
        assert ds.title == "Population Projections"

    async def test_not_found(self, async_client):
        with pytest.raises(DatasetNotFoundError):
            await async_client.get_dataset("nonexistent")

    async def test_v2_fields(self, async_client):
        ds = await async_client.get_dataset("cycling-infrastructure")
        assert ds.topics == ["transport"]
        assert ds.publisher == "Transport for London"


class TestAsyncGetAllTopics:
    async def test_returns_sorted(self, async_client):
        topics = await async_client.get_all_topics()
        assert topics == sorted(topics)
        assert "demographics" in topics
        assert "transport" in topics


class TestAsyncFilterByTopic:
    async def test_filter(self, async_client):
        slugs = await async_client.filter_by_topic("transport")
        assert "cycling-infrastructure" in slugs
        assert "population-projections" not in slugs


class TestAsyncFilterByKeyword:
    async def test_keyword_match(self, async_client):
        results = await async_client.filter_slugs_for_keyword("cycling")
        assert "cycling-infrastructure" in results


class TestAsyncClearCache:
    async def test_clear_cache_no_error(self, async_client):
        async_client.clear_cache()  # should not raise even with cache=False
