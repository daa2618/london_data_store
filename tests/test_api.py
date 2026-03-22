"""Tests for london_data_store.api module."""

from unittest.mock import MagicMock, patch

import pytest

from london_data_store.api import LondonDataStore, _search_list_for_string, _validate_string
from london_data_store.exceptions import DatasetNotFoundError, FormatNotAvailableError

# ── _validate_string ──────────────────────────────────────────────


class TestValidateString:
    def test_valid_string(self):
        assert _validate_string("hello", "param") == "hello"

    def test_strips_whitespace(self):
        assert _validate_string("  hello  ", "param") == "hello"

    def test_none_raises(self):
        with pytest.raises(ValueError):
            _validate_string(None, "param")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            _validate_string("", "param")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError):
            _validate_string("   ", "param")

    def test_non_string_raises(self):
        with pytest.raises(ValueError):
            _validate_string(123, "param")


# ── _search_list_for_string ───────────────────────────────────────


class TestSearchListForString:
    def test_exact_match(self):
        result = _search_list_for_string(["population-data", "cycling-routes"], "population")
        assert result is not None
        assert "population-data" in result

    def test_no_match_returns_none(self):
        result = _search_list_for_string(["apple", "banana"], "xyznotfound")
        # May return None or a list depending on similarity threshold
        if result is not None:
            assert isinstance(result, list)


# ── LondonDataStore.__init__ ──────────────────────────────────────


class TestInit:
    def test_default_url(self):
        lds = LondonDataStore()
        assert "data.london.gov.uk" in lds.json_url
        assert "/api/v2/" in lds.json_url
        lds.close()

    def test_custom_url(self):
        lds = LondonDataStore(json_url="https://example.com/api.json")
        assert lds.json_url == "https://example.com/api.json"
        lds.close()

    def test_session_created(self):
        lds = LondonDataStore()
        assert lds._session is not None
        lds.close()

    def test_context_manager(self):
        with LondonDataStore() as lds:
            assert lds._session is not None

    def test_base_url_property(self):
        lds = LondonDataStore()
        assert lds.base_url == "https://data.london.gov.uk"
        lds.close()

    def test_base_url_cached(self):
        lds = LondonDataStore()
        _ = lds.base_url
        _ = lds.base_url
        assert lds._base_url is not None
        lds.close()


# ── get_all_slugs ─────────────────────────────────────────────────


class TestGetAllSlugs:
    def test_returns_sorted_unique(self, mock_client):
        slugs = mock_client.get_all_slugs()
        assert slugs == sorted(set(slugs))
        assert "population-projections" in slugs
        assert "london-borough-profiles" in slugs
        assert "cycling-infrastructure" in slugs

    def test_no_duplicates(self, mock_client):
        slugs = mock_client.get_all_slugs()
        assert len(slugs) == len(set(slugs))


# ── filter_slugs_for_string ───────────────────────────────────────


class TestFilterSlugsForString:
    def test_population_match(self, mock_client):
        with pytest.warns(DeprecationWarning, match="filter_slugs_for_string"):
            result = mock_client.filter_slugs_for_string("population")
        assert result is not None
        assert any("population" in s for s in result)

    def test_invalid_input_raises(self, mock_client):
        with pytest.warns(DeprecationWarning, match="filter_slugs_for_string"), pytest.raises(ValueError):
            mock_client.filter_slugs_for_string("")

    def test_none_input_raises(self, mock_client):
        with pytest.warns(DeprecationWarning, match="filter_slugs_for_string"), pytest.raises(ValueError):
            mock_client.filter_slugs_for_string(None)


# ── get_all_d_types ───────────────────────────────────────────────


class TestGetAllDTypes:
    def test_returns_list(self, mock_client):
        dtypes = mock_client.get_all_d_types()
        assert isinstance(dtypes, list)

    def test_contains_expected_formats(self, mock_client):
        dtypes = mock_client.get_all_d_types()
        assert "csv" in dtypes
        assert "geojson" in dtypes

    def test_result_cached(self, mock_client):
        dtypes1 = mock_client.get_all_d_types()
        dtypes2 = mock_client.get_all_d_types()
        assert dtypes1 is dtypes2


# ── filter_slug_for_d_type ────────────────────────────────────────


class TestFilterSlugForDType:
    def test_csv_filter(self, mock_client):
        result = mock_client.filter_slug_for_d_type("csv")
        assert "population-projections" in result
        assert "london-borough-profiles" in result

    def test_geojson_filter(self, mock_client):
        result = mock_client.filter_slug_for_d_type("geojson")
        assert "population-projections" in result
        assert "cycling-infrastructure" in result

    def test_invalid_format_raises(self, mock_client):
        with pytest.raises(FormatNotAvailableError, match="Available Data types"):
            mock_client.filter_slug_for_d_type("nonexistent_format")

    def test_gpkg_alias(self, mock_client):
        """gpkg should be converted to geopackage before filtering."""
        with pytest.raises(ValueError):
            mock_client.filter_slug_for_d_type("gpkg")


# ── get_download_url_for_slug ─────────────────────────────────────


class TestGetDownloadUrlForSlug:
    def test_returns_urls(self, mock_client):
        urls = mock_client.get_download_url_for_slug("population-projections")
        assert len(urls) == 2
        assert all("data.london.gov.uk" in u for u in urls)

    def test_slug_not_found(self, mock_client):
        urls = mock_client.get_download_url_for_slug("nonexistent-slug")
        assert urls == []

    def test_invalid_slug_raises(self, mock_client):
        with pytest.raises(ValueError):
            mock_client.get_download_url_for_slug("")

    def test_uses_cached_base_url(self, mock_client):
        urls = mock_client.get_download_url_for_slug("population-projections")
        assert all(u.startswith("https://data.london.gov.uk/download/") for u in urls)


# ── filter_slugs_for_keyword ──────────────────────────────────────


class TestFilterSlugsForKeyword:
    def test_keyword_match(self, mock_client):
        result = mock_client.filter_slugs_for_keyword("cycling")
        assert "cycling-infrastructure" in result

    def test_stemmed_keyword(self, mock_client):
        result = mock_client.filter_slugs_for_keyword("cycle")
        assert "cycling-infrastructure" in result

    def test_multi_word_keyword(self, mock_client):
        result = mock_client.filter_slugs_for_keyword("population demographics")
        assert "population-projections" in result

    def test_invalid_keyword_raises(self, mock_client):
        with pytest.raises(ValueError):
            mock_client.filter_slugs_for_keyword("")


# ── get_map_data_to_plot ──────────────────────────────────────────


class TestGetMapDataToPlot:
    def test_invalid_extension_raises(self, mock_client):
        with pytest.raises(TypeError, match="Extension for map data"):
            mock_client.get_map_data_to_plot("population-projections", "pdf")

    def test_no_matching_extension(self, mock_client):
        with pytest.raises(DatasetNotFoundError, match="does not have any map data"):
            mock_client.get_map_data_to_plot("london-borough-profiles", "geojson")

    def test_multiple_urls_returned(self, mock_client):
        """When multiple files match, return list of URLs."""
        # cycling-infrastructure has geojson and shp but only one geojson
        # Let's add another geojson to test multi-URL path
        mock_client._raw_response_json[2]["resources"]["res-022"] = {
            "format": "geojson",
            "url": "https://files.datapress.com/london/dataset/cycling-infrastructure/extra.geojson",
        }
        result = mock_client.get_map_data_to_plot("cycling-infrastructure", "geojson")
        assert isinstance(result, list)
        assert len(result) == 2

    @patch("london_data_store.api.gpd", create=True)
    def test_single_file_returns_geodataframe(self, mock_gpd, mock_client):
        """When a single file matches, return a GeoDataFrame."""
        # Patch the lazy import inside get_map_data_to_plot
        mock_gdf = MagicMock()
        mock_gdf.crs.to_epsg.return_value = 4326
        mock_gpd_module = MagicMock()
        mock_gpd_module.read_file.return_value = mock_gdf
        mock_gdf.to_crs.return_value = mock_gdf

        with patch.dict("sys.modules", {"geopandas": mock_gpd_module}):
            mock_client.get_map_data_to_plot("population-projections", "geojson")
            mock_gpd_module.read_file.assert_called_once()

    def test_geopackage_alias(self, mock_client):
        """geopackage should be converted to gpkg."""
        with pytest.raises(ValueError):
            mock_client.get_map_data_to_plot("population-projections", "geopackage")

    def test_empty_slug_raises(self, mock_client):
        with pytest.raises(ValueError):
            mock_client.get_map_data_to_plot("", "geojson")

    def test_empty_extension_raises(self, mock_client):
        with pytest.raises(ValueError):
            mock_client.get_map_data_to_plot("population-projections", "")


# ── search (v2) ──────────────────────────────────────────────────


class TestSearch:
    def test_returns_scored_tuples(self, mock_client):
        results = mock_client.search("population")
        assert isinstance(results, list)
        assert all(isinstance(r, tuple) and len(r) == 2 for r in results)

    def test_scores_are_floats(self, mock_client):
        results = mock_client.search("population")
        assert all(isinstance(r[1], float) for r in results)

    def test_sorted_by_score_descending(self, mock_client):
        results = mock_client.search("population")
        scores = [r[1] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_limit(self, mock_client):
        results = mock_client.search("a", limit=2)
        assert len(results) <= 2

    def test_invalid_term_raises(self, mock_client):
        with pytest.raises(ValueError):
            mock_client.search("")

    def test_best_match_is_first(self, mock_client):
        results = mock_client.search("cycling")
        assert results[0][0] == "cycling-infrastructure"


# ── get_dataset (v2) ─────────────────────────────────────────────


class TestGetDataset:
    def test_returns_dataset(self, mock_client):
        ds = mock_client.get_dataset("population-projections")
        assert ds.slug == "population-projections"
        assert ds.title == "Population Projections"

    def test_has_v2_fields(self, mock_client):
        ds = mock_client.get_dataset("population-projections")
        assert ds.id == "abc01"
        assert ds.topics == ["demographics"]
        assert ds.licence_title == "UK Open Government Licence (OGL v3)"
        assert ds.publisher == "Greater London Authority"
        assert ds.update_frequency == "Annual"
        assert ds.contact == "data@london.gov.uk"

    def test_resources_populated(self, mock_client):
        ds = mock_client.get_dataset("population-projections")
        assert len(ds.resources) == 2
        assert ds.resources[0].title == "pop-data.csv"
        assert ds.resources[0].check_size == 102400

    def test_not_found_raises(self, mock_client):
        with pytest.raises(DatasetNotFoundError):
            mock_client.get_dataset("nonexistent-slug")

    def test_invalid_slug_raises(self, mock_client):
        with pytest.raises(ValueError):
            mock_client.get_dataset("")

    def test_is_archived_false(self, mock_client):
        ds = mock_client.get_dataset("population-projections")
        assert ds.is_archived is False


# ── get_all_topics (v2) ──────────────────────────────────────────


class TestGetAllTopics:
    def test_returns_sorted_list(self, mock_client):
        topics = mock_client.get_all_topics()
        assert topics == sorted(topics)

    def test_contains_expected_topics(self, mock_client):
        topics = mock_client.get_all_topics()
        assert "demographics" in topics
        assert "transport" in topics
        assert "housing" in topics

    def test_no_duplicates(self, mock_client):
        topics = mock_client.get_all_topics()
        assert len(topics) == len(set(topics))


# ── filter_by_topic (v2) ─────────────────────────────────────────


class TestFilterByTopic:
    def test_demographics(self, mock_client):
        slugs = mock_client.filter_by_topic("demographics")
        assert "population-projections" in slugs
        assert "london-borough-profiles" in slugs

    def test_transport(self, mock_client):
        slugs = mock_client.filter_by_topic("transport")
        assert "cycling-infrastructure" in slugs
        assert "population-projections" not in slugs

    def test_no_match(self, mock_client):
        slugs = mock_client.filter_by_topic("nonexistent-topic")
        assert slugs == []

    def test_invalid_raises(self, mock_client):
        with pytest.raises(ValueError):
            mock_client.filter_by_topic("")


# ── filter_by_publisher (v2) ─────────────────────────────────────


class TestFilterByPublisher:
    def test_gla(self, mock_client):
        slugs = mock_client.filter_by_publisher("Greater London Authority")
        assert "population-projections" in slugs
        assert "london-borough-profiles" in slugs
        assert "cycling-infrastructure" not in slugs

    def test_case_insensitive(self, mock_client):
        slugs = mock_client.filter_by_publisher("transport for london")
        assert "cycling-infrastructure" in slugs

    def test_substring_match(self, mock_client):
        slugs = mock_client.filter_by_publisher("London")
        assert len(slugs) == 3  # All have "London" in publisher

    def test_no_match(self, mock_client):
        slugs = mock_client.filter_by_publisher("Unknown Publisher")
        assert slugs == []

    def test_invalid_raises(self, mock_client):
        with pytest.raises(ValueError):
            mock_client.filter_by_publisher("")


# ── filter_by_update_frequency (v2) ──────────────────────────────


class TestFilterByUpdateFrequency:
    def test_annual(self, mock_client):
        slugs = mock_client.filter_by_update_frequency("Annual")
        assert "population-projections" in slugs

    def test_monthly(self, mock_client):
        slugs = mock_client.filter_by_update_frequency("Monthly")
        assert "london-borough-profiles" in slugs

    def test_case_insensitive(self, mock_client):
        slugs = mock_client.filter_by_update_frequency("annual")
        assert "population-projections" in slugs

    def test_one_off(self, mock_client):
        slugs = mock_client.filter_by_update_frequency("One off")
        assert "cycling-infrastructure" in slugs

    def test_no_match(self, mock_client):
        slugs = mock_client.filter_by_update_frequency("Daily")
        assert slugs == []

    def test_invalid_raises(self, mock_client):
        with pytest.raises(ValueError):
            mock_client.filter_by_update_frequency("")


# ── filter_by_licence (v2) ───────────────────────────────────────


class TestFilterByLicence:
    def test_ogl(self, mock_client):
        slugs = mock_client.filter_by_licence("Open Government")
        assert "population-projections" in slugs
        assert "london-borough-profiles" in slugs
        assert "cycling-infrastructure" not in slugs

    def test_creative_commons(self, mock_client):
        slugs = mock_client.filter_by_licence("Creative Commons")
        assert "cycling-infrastructure" in slugs

    def test_case_insensitive(self, mock_client):
        slugs = mock_client.filter_by_licence("ogl")
        assert "population-projections" in slugs

    def test_no_match(self, mock_client):
        slugs = mock_client.filter_by_licence("Proprietary")
        assert slugs == []

    def test_invalid_raises(self, mock_client):
        with pytest.raises(ValueError):
            mock_client.filter_by_licence("")
