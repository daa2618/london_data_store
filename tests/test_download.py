"""Tests for london_data_store.download module."""

from unittest.mock import MagicMock, patch

import pytest

from london_data_store.download import DownloadManager
from london_data_store.exceptions import DatasetNotFoundError, DownloadError, FormatNotAvailableError


class TestDownloadManager:
    def _make_response(
        self, content: bytes = b"test file content", status_code: int = 200, content_length: int | None = None
    ):
        response = MagicMock()
        response.status_code = status_code
        response.headers = {}
        if content_length is not None:
            response.headers["content-length"] = str(content_length)
        response.iter_content.return_value = [content]
        response.raise_for_status.return_value = None
        return response

    def test_basic_download(self, tmp_path):
        session = MagicMock()
        content = b"hello world"
        session.get.return_value = self._make_response(content)

        manager = DownloadManager(session)
        result = manager.download_file("https://example.com/data.csv", tmp_path)

        assert result == tmp_path / "data.csv"
        assert result.read_bytes() == content

    def test_download_to_specific_file(self, tmp_path):
        session = MagicMock()
        session.get.return_value = self._make_response(b"data")

        dest = tmp_path / "output.csv"
        manager = DownloadManager(session)
        result = manager.download_file("https://example.com/data.csv", dest)

        assert result == dest
        assert dest.read_bytes() == b"data"

    def test_progress_callback(self, tmp_path):
        session = MagicMock()
        content = b"chunk_data"
        session.get.return_value = self._make_response(content, content_length=len(content))

        callback = MagicMock()
        manager = DownloadManager(session)
        manager.download_file("https://example.com/data.csv", tmp_path, progress_callback=callback)

        callback.assert_called_once_with(len(content), len(content))

    def test_http_error_raises(self, tmp_path):
        session = MagicMock()
        import requests

        session.get.side_effect = requests.ConnectionError("connection failed")

        manager = DownloadManager(session)
        with pytest.raises(DownloadError, match="Failed to download"):
            manager.download_file("https://example.com/data.csv", tmp_path)

    def test_size_mismatch_raises(self, tmp_path):
        session = MagicMock()
        session.get.return_value = self._make_response(b"short")

        manager = DownloadManager(session)
        with pytest.raises(DownloadError, match="Size mismatch"):
            manager.download_file("https://example.com/data.csv", tmp_path, expected_size=9999)

    def test_hash_mismatch_warns(self, tmp_path):
        """Hash mismatch should warn (stale catalogue metadata) but still download."""
        session = MagicMock()
        session.get.return_value = self._make_response(b"test data")

        manager = DownloadManager(session)
        result = manager.download_file("https://example.com/data.csv", tmp_path, expected_hash="0000000000000000")
        assert result.exists()

    def test_hash_with_version_suffix(self, tmp_path):
        import hashlib

        content = b"test data"
        expected = hashlib.md5(content).hexdigest()
        session = MagicMock()
        session.get.return_value = self._make_response(content)

        manager = DownloadManager(session)
        # Hash with version suffix should be stripped before comparison
        result = manager.download_file("https://example.com/data.csv", tmp_path, expected_hash=f"{expected}-1")
        assert result.exists()

    def test_creates_parent_directories(self, tmp_path):
        session = MagicMock()
        session.get.return_value = self._make_response(b"data")

        dest = tmp_path / "sub" / "dir" / "output.csv"
        manager = DownloadManager(session)
        result = manager.download_file("https://example.com/data.csv", dest)

        assert result.exists()

    def test_no_part_file_on_success(self, tmp_path):
        session = MagicMock()
        session.get.return_value = self._make_response(b"data")

        manager = DownloadManager(session)
        manager.download_file("https://example.com/data.csv", tmp_path)

        # No .part files should remain
        part_files = list(tmp_path.glob("*.part"))
        assert part_files == []


class TestApiDownloadFile:
    def test_download_by_format(self, mock_client, tmp_path):
        with patch.object(DownloadManager, "download_file", return_value=tmp_path / "pop-data.csv") as mock_dl:
            result = mock_client.download_file("population-projections", format="csv", destination=tmp_path)
            assert result == tmp_path / "pop-data.csv"
            mock_dl.assert_called_once()
            call_kwargs = mock_dl.call_args
            assert "pop-data.csv" in call_kwargs.kwargs["url"]

    def test_download_by_resource_key(self, mock_client, tmp_path):
        with patch.object(DownloadManager, "download_file", return_value=tmp_path / "boundaries.geojson"):
            result = mock_client.download_file("population-projections", resource_key="res-002", destination=tmp_path)
            assert result == tmp_path / "boundaries.geojson"

    def test_download_default_first_resource(self, mock_client, tmp_path):
        with patch.object(DownloadManager, "download_file", return_value=tmp_path / "file.csv") as mock_dl:
            mock_client.download_file("population-projections", destination=tmp_path)
            mock_dl.assert_called_once()

    def test_slug_not_found(self, mock_client, tmp_path):
        with pytest.raises(DatasetNotFoundError):
            mock_client.download_file("nonexistent-slug", destination=tmp_path)

    def test_format_not_found(self, mock_client, tmp_path):
        with pytest.raises(FormatNotAvailableError, match="Format 'pdf'"):
            mock_client.download_file("population-projections", format="pdf", destination=tmp_path)

    def test_resource_key_not_found(self, mock_client, tmp_path):
        with pytest.raises(DatasetNotFoundError, match="Resource key"):
            mock_client.download_file("population-projections", resource_key="nonexistent", destination=tmp_path)

    def test_empty_slug_raises(self, mock_client, tmp_path):
        with pytest.raises(ValueError):
            mock_client.download_file("", destination=tmp_path)

    def test_verify_integrity_passes_hash_and_size(self, mock_client, tmp_path):
        with patch.object(DownloadManager, "download_file", return_value=tmp_path / "pop-data.csv") as mock_dl:
            mock_client.download_file(
                "population-projections", format="csv", destination=tmp_path, verify_integrity=True
            )
            call_kwargs = mock_dl.call_args.kwargs
            assert call_kwargs["expected_hash"] == "a361d1622b08e0a6335f489495399247-1"
            assert call_kwargs["expected_size"] == 102400

    def test_verify_integrity_disabled(self, mock_client, tmp_path):
        with patch.object(DownloadManager, "download_file", return_value=tmp_path / "pop-data.csv") as mock_dl:
            mock_client.download_file(
                "population-projections", format="csv", destination=tmp_path, verify_integrity=False
            )
            call_kwargs = mock_dl.call_args.kwargs
            assert call_kwargs["expected_hash"] is None
            assert call_kwargs["expected_size"] is None
