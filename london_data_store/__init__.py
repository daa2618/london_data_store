from .api import LondonDataStore
from .exceptions import (
    CacheError,
    DatasetNotFoundError,
    DownloadError,
    FormatNotAvailableError,
    LondonDataStoreError,
)
from .models import Dataset, Resource

__all__ = [
    "LondonDataStore",
    "Resource",
    "Dataset",
    "LondonDataStoreError",
    "DatasetNotFoundError",
    "FormatNotAvailableError",
    "DownloadError",
    "CacheError",
]

# Conditionally export AsyncLondonDataStore if httpx is available
try:
    from .async_client import AsyncLondonDataStore  # noqa: F401

    __all__.append("AsyncLondonDataStore")
except ImportError:
    pass
