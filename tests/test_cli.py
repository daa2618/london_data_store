"""Tests for london_data_store.cli module."""

import json
from unittest.mock import MagicMock, patch

import pytest

from london_data_store.cli import main


@pytest.fixture
def mock_lds(sample_catalogue):
    """Patch LondonDataStore to return pre-cached data."""
    with patch("london_data_store.cli.LondonDataStore") as MockCls:
        from london_data_store.api import LondonDataStore

        instance = LondonDataStore.__new__(LondonDataStore)
        instance.json_url = "https://data.london.gov.uk/api/v2/datasets/export.json"
        instance._raw_response_json = sample_catalogue
        instance._all_d_types = None
        instance._base_url = None
        instance._session = MagicMock()
        instance._cache = None

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

    def test_slugs_json(self, mock_lds, capsys):
        result = main(["slugs", "--json"])
        assert result == 0
        output = json.loads(capsys.readouterr().out)
        assert isinstance(output, list)
        assert "population-projections" in output

    def test_slugs_limit(self, mock_lds, capsys):
        result = main(["slugs", "--limit", "1"])
        assert result == 0
        output = capsys.readouterr().out.strip().split("\n")
        assert len(output) == 1


class TestSearchCommand:
    def test_search_found(self, mock_lds, capsys):
        result = main(["search", "population"])
        assert result == 0
        output = capsys.readouterr().out
        # Should show title, slug, and date
        assert "Population" in output
        assert "population-projections" in output
        assert "2025" in output

    def test_search_not_found(self, mock_lds, capsys):
        result = main(["search", "xyznonexistent"])
        # Could be 0 or 1 depending on fuzzy matching
        assert result in (0, 1)

    def test_search_scored(self, mock_lds, capsys):
        result = main(["search", "--scored", "cycling"])
        assert result == 0
        output = capsys.readouterr().out
        # Should contain score, title, and slug
        assert "Cycling Infrastructure" in output
        assert "cycling-infrastructure" in output
        # Score is a float like 0.xxxx
        lines = output.strip().split("\n")
        assert any("." in line.split()[0] for line in lines if line.strip())

    def test_search_scored_json(self, mock_lds, capsys):
        result = main(["search", "--json", "--scored", "cycling"])
        assert result == 0
        output = json.loads(capsys.readouterr().out)
        assert isinstance(output, list)
        assert output[0]["title"] == "Cycling Infrastructure"
        assert output[0]["slug"] == "cycling-infrastructure"
        assert "score" in output[0]
        assert "date" in output[0]


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
        assert "Cycling Infrastructure" in output

    def test_keywords_not_found(self, mock_lds, capsys):
        result = main(["keywords", "xyznonexistent"])
        assert result == 1


class TestInfoCommand:
    def test_info_output(self, mock_lds, capsys):
        result = main(["info", "population-projections"])
        assert result == 0
        output = capsys.readouterr().out
        assert "population-projections" in output
        assert "Greater London Authority" in output

    def test_info_json(self, mock_lds, capsys):
        result = main(["info", "population-projections", "--json"])
        assert result == 0
        output = json.loads(capsys.readouterr().out)
        assert output["slug"] == "population-projections"
        assert output["publisher"] == "Greater London Authority"

    def test_info_not_found(self, mock_lds, capsys):
        result = main(["info", "nonexistent"])
        assert result == 1


class TestTopicsCommand:
    def test_topics_list(self, mock_lds, capsys):
        result = main(["topics"])
        assert result == 0
        output = capsys.readouterr().out
        assert "demographics" in output
        assert "transport" in output

    def test_topics_filter(self, mock_lds, capsys):
        result = main(["topics", "--filter", "transport"])
        assert result == 0
        output = capsys.readouterr().out
        assert "cycling-infrastructure" in output
        assert "population-projections" not in output

    def test_topics_json(self, mock_lds, capsys):
        result = main(["topics", "--json"])
        assert result == 0
        output = json.loads(capsys.readouterr().out)
        assert "demographics" in output


class TestDownloadCommand:
    def test_download(self, mock_lds, capsys, tmp_path):
        with patch("london_data_store.api.DownloadManager") as MockDM:
            mock_dm = MagicMock()
            mock_dm.download_file.return_value = tmp_path / "pop-data.csv"
            MockDM.return_value = mock_dm

            result = main(["download", "population-projections", "--format", "csv", "--dest", str(tmp_path)])
            assert result == 0
            output = capsys.readouterr().out
            assert "Downloaded:" in output

    def test_download_not_found(self, mock_lds, capsys, tmp_path):
        result = main(["download", "nonexistent", "--dest", str(tmp_path)])
        assert result == 1


class TestNoCommand:
    def test_no_command_exits(self):
        with pytest.raises(SystemExit):
            main([])

    def test_no_cache_flag(self, mock_lds, capsys):
        """--no-cache should be accepted without error."""
        result = main(["slugs", "--no-cache"])
        assert result == 0
