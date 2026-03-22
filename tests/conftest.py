"""Shared fixtures for london_data_store tests."""

import pytest

SAMPLE_CATALOGUE = [
    {
        "id": "abc01",
        "slug": "population-projections",
        "title": "Population Projections",
        "canonical": "/dataset/population-projections-abc01",
        "tags": ["population", "demographics", "projections"],
        "topics": ["demographics"],
        "updatedAt": "2025-06-15T10:30:00+00:00",
        "createdAt": "2020-01-10T09:00:00+00:00",
        "archivedAt": None,
        "description": "Population projections for London boroughs",
        "licence": {
            "url": "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/",
            "title": "UK Open Government Licence (OGL v3)",
        },
        "contact": "data@london.gov.uk",
        "publisher": "Greater London Authority",
        "sharing": "public",
        "webpage": "https://data.london.gov.uk/dataset/population-projections",
        "parent": None,
        "team": "team-gla",
        "custom": {
            "geo": "Greater London",
            "author": "GLA Intelligence",
            "author_email": "intelligence@london.gov.uk",
            "update_frequency": "Annual",
        },
        "resources": {
            "res-001": {
                "format": "csv",
                "url": "https://files.datapress.com/london/dataset/population-projections/pop-data.csv",
                "title": "pop-data.csv",
                "description": "Population data CSV",
                "temporal_coverage_from": "2020-01-01",
                "temporal_coverage_to": "2025-12-31",
                "check_hash": "a361d1622b08e0a6335f489495399247-1",
                "check_size": 102400,
                "check_http_status": 200,
                "check_mimetype": "text/csv",
                "check_timestamp": "2025-06-15T10:00:00+00:00",
            },
            "res-002": {
                "format": "geojson",
                "url": "https://files.datapress.com/london/dataset/population-projections/boundaries.geojson",
                "title": "boundaries.geojson",
                "description": "Borough boundaries",
                "temporal_coverage_from": "2020-01-01",
                "temporal_coverage_to": "2025-12-31",
                "check_hash": "b472e2733c19f1b7446g590506400358-1",
                "check_size": 512000,
                "check_http_status": 200,
                "check_mimetype": "application/geo+json",
                "check_timestamp": "2025-06-15T10:00:00+00:00",
            },
        },
    },
    {
        "id": "def02",
        "slug": "london-borough-profiles",
        "title": "London Borough Profiles",
        "canonical": "/dataset/london-borough-profiles-def02",
        "tags": ["borough", "profiles", "statistics"],
        "topics": ["demographics", "housing"],
        "updatedAt": "2024-01-20T08:00:00+00:00",
        "createdAt": "2018-05-01T12:00:00+00:00",
        "archivedAt": None,
        "description": "Key statistics for London boroughs",
        "licence": {
            "url": "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/",
            "title": "UK Open Government Licence (OGL v3)",
        },
        "contact": "profiles@london.gov.uk",
        "publisher": "Greater London Authority",
        "sharing": "public",
        "webpage": "https://data.london.gov.uk/dataset/london-borough-profiles",
        "parent": None,
        "team": "team-gla",
        "custom": {
            "geo": "Greater London",
            "author": "GLA Intelligence",
            "author_email": "intelligence@london.gov.uk",
            "update_frequency": "Monthly",
        },
        "resources": {
            "res-010": {
                "format": "csv",
                "url": "https://files.datapress.com/london/dataset/london-borough-profiles/profiles.csv",
                "title": "profiles.csv",
                "description": "Borough profiles CSV",
                "temporal_coverage_from": "2018-01-01",
                "temporal_coverage_to": "2024-01-01",
                "check_hash": "c583f3844d20g2c8557h601617511469-1",
                "check_size": 204800,
                "check_http_status": 200,
                "check_mimetype": "text/csv",
                "check_timestamp": "2024-01-20T07:00:00+00:00",
            },
        },
    },
    {
        "id": "ghi03",
        "slug": "cycling-infrastructure",
        "title": "Cycling Infrastructure",
        "canonical": "/dataset/cycling-infrastructure-ghi03",
        "tags": ["cycling", "transport", "infrastructure"],
        "topics": ["transport"],
        "updatedAt": "2025-11-01T14:00:00+00:00",
        "createdAt": "2019-03-15T10:00:00+00:00",
        "archivedAt": None,
        "description": "Cycling infrastructure data",
        "licence": {
            "url": "https://creativecommons.org/licenses/by/4.0/",
            "title": "Creative Commons Attribution 4.0",
        },
        "contact": "transport@tfl.gov.uk",
        "publisher": "Transport for London",
        "sharing": "public",
        "webpage": "https://data.london.gov.uk/dataset/cycling-infrastructure",
        "parent": None,
        "team": "team-tfl",
        "custom": {
            "geo": "Greater London",
            "author": "TfL Open Data",
            "author_email": "opendata@tfl.gov.uk",
            "update_frequency": "One off",
        },
        "resources": {
            "res-020": {
                "format": "geojson",
                "url": "https://files.datapress.com/london/dataset/cycling-infrastructure/routes.geojson",
                "title": "routes.geojson",
                "description": "Cycling routes GeoJSON",
                "temporal_coverage_from": "",
                "temporal_coverage_to": "",
                "check_hash": "d694g4955e31h3d9668i712728622570-1",
                "check_size": 1048576,
                "check_http_status": 200,
                "check_mimetype": "application/geo+json",
                "check_timestamp": "2025-11-01T13:00:00+00:00",
            },
            "res-021": {
                "format": "shp",
                "url": "https://files.datapress.com/london/dataset/cycling-infrastructure/routes.shp",
                "title": "routes.shp",
                "description": "Cycling routes Shapefile",
                "temporal_coverage_from": "",
                "temporal_coverage_to": "",
                "check_hash": "e705h5066f42i4e0779j823839733681-1",
                "check_size": 2097152,
                "check_http_status": 200,
                "check_mimetype": "application/x-shapefile",
                "check_timestamp": "2025-11-01T13:00:00+00:00",
            },
        },
    },
]


@pytest.fixture
def sample_catalogue():
    """Return sample catalogue data."""
    return SAMPLE_CATALOGUE


@pytest.fixture
def mock_client(sample_catalogue):
    """Return a LondonDataStore client with mocked HTTP responses."""
    from london_data_store.api import LondonDataStore

    client = LondonDataStore()
    client._raw_response_json = sample_catalogue
    return client
