"""Tests for london_data_store.models module."""

from london_data_store.models import Dataset, Resource


class TestResource:
    def test_creation(self):
        r = Resource(key="res-001", url="https://example.com/data.csv", format="csv")
        assert r.key == "res-001"
        assert r.format == "csv"

    def test_to_dict(self):
        r = Resource(key="res-001", url="https://example.com/data.csv", format="csv")
        d = r.to_dict()
        assert d == {"key": "res-001", "url": "https://example.com/data.csv", "format": "csv"}


class TestDataset:
    def test_creation_minimal(self):
        ds = Dataset(slug="test-slug")
        assert ds.slug == "test-slug"
        assert ds.tags == []
        assert ds.resources == []

    def test_creation_full(self):
        r = Resource(key="r1", url="https://example.com/f.csv", format="csv")
        ds = Dataset(
            slug="my-dataset",
            tags=["tag1", "tag2"],
            updated_at="2025-01-01T00:00:00Z",
            description="Test dataset",
            resources=[r],
        )
        assert ds.slug == "my-dataset"
        assert len(ds.resources) == 1

    def test_to_dict(self):
        ds = Dataset(slug="test", tags=["a"])
        d = ds.to_dict()
        assert d["slug"] == "test"
        assert d["tags"] == ["a"]

    def test_from_api_dict(self):
        raw = {
            "slug": "population-data",
            "tags": ["population"],
            "updatedAt": "2025-06-15T10:30:00+00:00",
            "description": "Pop data",
            "resources": {
                "res-001": {"url": "https://example.com/pop.csv", "format": "csv"},
                "res-002": {"url": "https://example.com/pop.geojson", "format": "geojson"},
            },
        }
        ds = Dataset.from_api_dict(raw)
        assert ds.slug == "population-data"
        assert len(ds.resources) == 2
        assert ds.resources[0].key == "res-001"
        assert ds.resources[0].format == "csv"

    def test_from_api_dict_empty_resources(self):
        raw = {"slug": "empty", "resources": {}}
        ds = Dataset.from_api_dict(raw)
        assert ds.resources == []

    def test_from_api_dict_missing_fields(self):
        raw = {"slug": "minimal"}
        ds = Dataset.from_api_dict(raw)
        assert ds.slug == "minimal"
        assert ds.tags == []
        assert ds.description is None
