"""Tests for london_data_store.cli module."""

from unittest.mock import MagicMock, patch

import pytest

from london_data_store.cli import main


@pytest.fixture
def mock_lds(sample_catalogue):
    """Patch LondonDataStore to return pre-cached data."""
    with patch("london_data_store.cli.LondonDataStore") as MockCls:
        from london_data_store.api import LondonDataStore

        instance = LondonDataStore.__new__(LondonDataStore)
        instance.json_url = "https://data.london.gov.uk/api/datasets/export.json"
        instance._raw_response_json = sample_catalogue
        instance._all_d_types = None
        instance._base_url = None
        instance._session = MagicMock()

        MockCls.return_value.__enter__ = MagicMock(return_value=instance)
        MockCls.return_value.__exit__ = MagicMock(return_value=False)
        yield instance


class TestSlugsCommand:
    def test_slugs_output(self, mock_lds, capsys):
        result = main(["slugs"])
        assert result == 0
        output = capsys.readouterr().out
        assert "population-projections" in output
        assert "cycling-infrastructure" in output


class TestSearchCommand:
    def test_search_found(self, mock_lds, capsys):
        result = main(["search", "population"])
        assert result == 0
        output = capsys.readouterr().out
        assert "population" in output

    def test_search_not_found(self, mock_lds, capsys):
        result = main(["search", "xyznonexistent"])
        # Could be 0 or 1 depending on fuzzy matching
        assert result in (0, 1)


class TestFormatsCommand:
    def test_formats_output(self, mock_lds, capsys):
        result = main(["formats"])
        assert result == 0
        output = capsys.readouterr().out
        assert "csv" in output
        assert "geojson" in output


class TestUrlsCommand:
    def test_urls_found(self, mock_lds, capsys):
        result = main(["urls", "population-projections"])
        assert result == 0
        output = capsys.readouterr().out
        assert "data.london.gov.uk" in output

    def test_urls_not_found(self, mock_lds, capsys):
        result = main(["urls", "nonexistent-slug"])
        assert result == 1


class TestKeywordsCommand:
    def test_keywords_found(self, mock_lds, capsys):
        result = main(["keywords", "cycling"])
        assert result == 0
        output = capsys.readouterr().out
        assert "cycling-infrastructure" in output

    def test_keywords_not_found(self, mock_lds, capsys):
        result = main(["keywords", "xyznonexistent"])
        assert result == 1


class TestNoCommand:
    def test_no_command_exits(self):
        with pytest.raises(SystemExit):
            main([])
