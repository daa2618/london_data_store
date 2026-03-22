"""Custom exceptions for the london_data_store library."""


class LondonDataStoreError(Exception):
    """Base exception for all london_data_store errors."""


class DatasetNotFoundError(LondonDataStoreError, ValueError):
    """Raised when a dataset slug cannot be found in the catalogue."""


class FormatNotAvailableError(LondonDataStoreError, ValueError):
    """Raised when a requested format does not exist for a dataset."""


class DownloadError(LondonDataStoreError):
    """Raised when a file download fails."""


class CacheError(LondonDataStoreError):
    """Raised when catalogue caching fails."""
