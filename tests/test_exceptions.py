"""Tests for london_data_store.exceptions module."""

from london_data_store.exceptions import (
    CacheError,
    DatasetNotFoundError,
    DownloadError,
    FormatNotAvailableError,
    LondonDataStoreError,
)


class TestExceptionHierarchy:
    def test_base_is_exception(self):
        assert issubclass(LondonDataStoreError, Exception)

    def test_dataset_not_found_is_value_error(self):
        """Backward compat: existing `except ValueError` should still catch it."""
        err = DatasetNotFoundError("not found")
        assert isinstance(err, ValueError)
        assert isinstance(err, LondonDataStoreError)

    def test_format_not_available_is_value_error(self):
        err = FormatNotAvailableError("bad format")
        assert isinstance(err, ValueError)
        assert isinstance(err, LondonDataStoreError)

    def test_download_error_is_base(self):
        err = DownloadError("download failed")
        assert isinstance(err, LondonDataStoreError)
        assert not isinstance(err, ValueError)

    def test_cache_error_is_base(self):
        err = CacheError("cache broken")
        assert isinstance(err, LondonDataStoreError)
        assert not isinstance(err, ValueError)

    def test_message_preserved(self):
        err = DatasetNotFoundError("slug 'foo' not found")
        assert str(err) == "slug 'foo' not found"

    def test_catch_by_base(self):
        """All custom exceptions should be catchable via the base class."""
        for exc_class in [DatasetNotFoundError, FormatNotAvailableError, DownloadError, CacheError]:
            try:
                raise exc_class("test")
            except LondonDataStoreError:
                pass
