"""Tests for london_data_store.models module."""

from london_data_store.models import Dataset, Resource


class TestResource:
    def test_creation(self):
        r = Resource(key="res-001", url="https://example.com/data.csv", format="csv")
        assert r.key == "res-001"
        assert r.format == "csv"

    def test_to_dict_minimal(self):
        r = Resource(key="res-001", url="https://example.com/data.csv", format="csv")
        d = r.to_dict()
        assert d["key"] == "res-001"
        assert d["url"] == "https://example.com/data.csv"
        assert d["format"] == "csv"
        assert d["title"] is None

    def test_v2_fields(self):
        r = Resource(
            key="res-001",
            url="https://example.com/data.csv",
            format="csv",
            title="data.csv",
            description="Test CSV",
            check_hash="abc123-1",
            check_size=1024,
            check_http_status=200,
            check_mimetype="text/csv",
            temporal_coverage_from="2020-01-01",
            temporal_coverage_to="2025-12-31",
            check_timestamp="2025-01-01T00:00:00Z",
        )
        assert r.title == "data.csv"
        assert r.check_hash == "abc123-1"
        assert r.check_size == 1024
        assert r.check_http_status == 200
        assert r.check_mimetype == "text/csv"
        assert r.temporal_coverage_from == "2020-01-01"
        assert r.temporal_coverage_to == "2025-12-31"

    def test_v2_fields_default_none(self):
        r = Resource(key="r1", url="http://x", format="csv")
        assert r.title is None
        assert r.check_hash is None
        assert r.check_size is None


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

    def test_v2_fields(self):
        ds = Dataset(
            slug="test",
            id="abc01",
            title="Test Dataset",
            topics=["transport"],
            licence_url="https://example.com/licence",
            licence_title="OGL v3",
            publisher="GLA",
            update_frequency="Annual",
            contact="test@example.com",
            created_at="2020-01-01T00:00:00Z",
            archived_at=None,
            webpage="https://example.com/dataset/test",
            geo="Greater London",
            author="Test Author",
            author_email="author@example.com",
        )
        assert ds.id == "abc01"
        assert ds.title == "Test Dataset"
        assert ds.topics == ["transport"]
        assert ds.licence_url == "https://example.com/licence"
        assert ds.publisher == "GLA"
        assert ds.update_frequency == "Annual"
        assert ds.is_archived is False

    def test_is_archived_true(self):
        ds = Dataset(slug="old", archived_at="2024-01-01T00:00:00Z")
        assert ds.is_archived is True

    def test_is_archived_false(self):
        ds = Dataset(slug="active")
        assert ds.is_archived is False

    def test_from_api_dict_full_v2(self, sample_catalogue):
        """Test from_api_dict with the enriched sample catalogue."""
        raw = sample_catalogue[0]  # population-projections
        ds = Dataset.from_api_dict(raw)
        assert ds.id == "abc01"
        assert ds.title == "Population Projections"
        assert ds.canonical == "/dataset/population-projections-abc01"
        assert ds.topics == ["demographics"]
        assert ds.licence_url == "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/"
        assert ds.licence_title == "UK Open Government Licence (OGL v3)"
        assert ds.contact == "data@london.gov.uk"
        assert ds.publisher == "Greater London Authority"
        assert ds.update_frequency == "Annual"
        assert ds.geo == "Greater London"
        assert ds.author == "GLA Intelligence"
        assert ds.author_email == "intelligence@london.gov.uk"
        assert ds.created_at == "2020-01-10T09:00:00+00:00"
        assert ds.archived_at is None
        assert ds.is_archived is False
        # Resource v2 fields
        res = ds.resources[0]
        assert res.title == "pop-data.csv"
        assert res.check_hash == "a361d1622b08e0a6335f489495399247-1"
        assert res.check_size == 102400
        assert res.check_http_status == 200
        assert res.temporal_coverage_from == "2020-01-01"

    def test_from_api_dict_nested_licence(self):
        raw = {
            "slug": "test",
            "licence": {"url": "https://example.com/lic", "title": "MIT"},
        }
        ds = Dataset.from_api_dict(raw)
        assert ds.licence_url == "https://example.com/lic"
        assert ds.licence_title == "MIT"

    def test_from_api_dict_missing_licence(self):
        raw = {"slug": "test"}
        ds = Dataset.from_api_dict(raw)
        assert ds.licence_url is None
        assert ds.licence_title is None

    def test_from_api_dict_custom_fields(self):
        raw = {
            "slug": "test",
            "custom": {"geo": "London", "author": "Author", "author_email": "a@b.com", "update_frequency": "Monthly"},
        }
        ds = Dataset.from_api_dict(raw)
        assert ds.geo == "London"
        assert ds.author == "Author"
        assert ds.author_email == "a@b.com"
        assert ds.update_frequency == "Monthly"
