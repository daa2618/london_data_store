"""Shared fixtures for london_data_store tests."""

import pytest

SAMPLE_CATALOGUE = [
    {
        "slug": "population-projections",
        "tags": ["population", "demographics", "projections"],
        "updatedAt": "2025-06-15T10:30:00+00:00",
        "description": "Population projections for London boroughs",
        "resources": {
            "res-001": {
                "format": "csv",
                "url": "https://files.datapress.com/london/dataset/population-projections/pop-data.csv",
            },
            "res-002": {
                "format": "geojson",
                "url": "https://files.datapress.com/london/dataset/population-projections/boundaries.geojson",
            },
        },
    },
    {
        "slug": "london-borough-profiles",
        "tags": ["borough", "profiles", "statistics"],
        "updatedAt": "2024-01-20T08:00:00+00:00",
        "description": "Key statistics for London boroughs",
        "resources": {
            "res-010": {
                "format": "csv",
                "url": "https://files.datapress.com/london/dataset/london-borough-profiles/profiles.csv",
            },
        },
    },
    {
        "slug": "cycling-infrastructure",
        "tags": ["cycling", "transport", "infrastructure"],
        "updatedAt": "2025-11-01T14:00:00+00:00",
        "description": "Cycling infrastructure data",
        "resources": {
            "res-020": {
                "format": "geojson",
                "url": "https://files.datapress.com/london/dataset/cycling-infrastructure/routes.geojson",
            },
            "res-021": {
                "format": "shp",
                "url": "https://files.datapress.com/london/dataset/cycling-infrastructure/routes.shp",
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
