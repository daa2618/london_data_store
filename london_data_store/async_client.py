"""Async version of LondonDataStore using httpx."""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlsplit

try:
    import httpx
except ImportError:
    raise ImportError(
        "httpx is required for async support. Install it with: pip install london-data-store[async]"
    ) from None

from .cache import CatalogueCache
from .exceptions import DatasetNotFoundError, FormatNotAvailableError
from .models import Dataset
from .utils.logging_helper import BasicLogger
from .utils.strings_and_lists import ListOperations

_bl = BasicLogger(verbose=False, log_directory=None, logger_name="ASYNC_LDS")

_stemmer = None


def _get_stemmer():
    global _stemmer
    if _stemmer is None:
        from nltk.stem.snowball import SnowballStemmer

        _stemmer = SnowballStemmer("english")
    return _stemmer


def _validate_string(value: object, param_name: str = "parameter") -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"'{param_name}' must be a non-empty string, got: {value!r}")
    return value.strip()


class AsyncLondonDataStore:
    """Async version of LondonDataStore using httpx.

    Args:
        json_url: The URL of the JSON dataset catalogue.
        cache: Whether to use disk caching.
        cache_ttl: Cache time-to-live in seconds.
        cache_dir: Custom cache directory.
    """

    def __init__(
        self,
        json_url: str = "https://data.london.gov.uk/api/v2/datasets/export.json",
        cache: bool = True,
        cache_ttl: int = 86400,
        cache_dir: Path | None = None,
    ):
        self.json_url = json_url
        self._raw_response_json: list[dict] | None = None
        self._client: httpx.AsyncClient | None = None
        self._cache = CatalogueCache(cache_dir=cache_dir, ttl_seconds=cache_ttl) if cache else None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={"User-Agent": "london-data-store-async/0.2.0"},
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> AsyncLondonDataStore:
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()

    @property
    def base_url(self) -> str:
        parts = urlsplit(self.json_url)
        return f"{parts.scheme}://{parts.netloc}"

    async def get_data_from_url(self) -> list[dict]:
        """Fetch and cache the full catalogue JSON."""
        if self._raw_response_json is None:
            if self._cache is not None:
                cached = self._cache.get(self.json_url)
                if cached is not None:
                    self._raw_response_json = cached
                    return self._raw_response_json

            client = await self._get_client()
            response = await client.get(self.json_url)
            response.raise_for_status()
            self._raw_response_json = response.json()

            if self._cache is not None:
                self._cache.put(self.json_url, self._raw_response_json)
        return self._raw_response_json

    async def get_all_slugs(self) -> list[str]:
        data = await self.get_data_from_url()
        slugs = sorted(set(x.get("slug") for x in data))
        return slugs

    async def search(self, term: str, limit: int = 20) -> list[tuple[str, float]]:
        _validate_string(term, "term")
        slugs = await self.get_all_slugs()
        list_ops = ListOperations(slugs, search_string=term)
        scored = list_ops.search_list_with_scores()
        return scored[:limit]

    async def get_dataset(self, slug: str) -> Dataset:
        _validate_string(slug, "slug")
        data = await self.get_data_from_url()
        for item in data:
            if item.get("slug") == slug:
                return Dataset.from_api_dict(item)
        raise DatasetNotFoundError(f"Dataset with slug '{slug}' not found")

    async def get_all_topics(self) -> list[str]:
        data = await self.get_data_from_url()
        topics = set()
        for item in data:
            for topic in item.get("topics", []):
                topics.add(topic)
        return sorted(topics)

    async def filter_by_topic(self, topic: str) -> list[str]:
        _validate_string(topic, "topic")
        data = await self.get_data_from_url()
        return [x.get("slug") for x in data if topic in x.get("topics", [])]

    async def filter_slugs_for_keyword(self, keyword: str) -> list[str]:
        _validate_string(keyword, "keyword")
        stemmer = _get_stemmer()
        search_terms = [stemmer.stem(x) for x in re.sub("[-_]", " ", keyword.strip().lower()).split(" ")]
        data = await self.get_data_from_url()
        return [
            x.get("slug")
            for x in data
            if any(word in y for y in [stemmer.stem(z) for z in x.get("tags")] for word in search_terms)
        ]

    async def download_file(
        self,
        slug: str,
        format: str | None = None,
        destination: str | Path = ".",
        *,
        resource_key: str | None = None,
        progress_callback: Callable[[int, int | None], None] | None = None,
        verify_integrity: bool = True,
    ) -> Path:
        """Download a resource file asynchronously."""
        _validate_string(slug, "slug")
        dataset = await self.get_dataset(slug)

        resource = None
        if resource_key:
            for r in dataset.resources:
                if r.key == resource_key:
                    resource = r
                    break
            if resource is None:
                raise DatasetNotFoundError(f"Resource key '{resource_key}' not found in dataset '{slug}'")
        elif format:
            fmt = format.lower()
            if fmt == "gpkg":
                fmt = "geopackage"
            for r in dataset.resources:
                if r.format.lower() == fmt:
                    resource = r
                    break
            if resource is None:
                available = [r.format for r in dataset.resources]
                raise FormatNotAvailableError(
                    f"Format '{format}' not found for slug '{slug}'. Available: {', '.join(available)}"
                )
        else:
            if not dataset.resources:
                raise DatasetNotFoundError(f"No resources found for slug '{slug}'")
            resource = dataset.resources[0]

        url_path = urlsplit(resource.url).path.split("/")[-1]
        download_url = f"{self.base_url}/download/{slug}/{resource.key}/{url_path}"

        destination = Path(destination)
        if destination.is_dir():
            filename = url_path or "download"
            destination = destination / filename

        destination.parent.mkdir(parents=True, exist_ok=True)

        client = await self._get_client()
        async with client.stream("GET", download_url) as response:
            response.raise_for_status()
            total = int(response.headers.get("content-length", 0)) or None
            bytes_downloaded = 0

            with open(destination, "wb") as f:
                async for chunk in response.aiter_bytes(8192):
                    f.write(chunk)
                    bytes_downloaded += len(chunk)
                    if progress_callback:
                        progress_callback(bytes_downloaded, total)

        _bl.info(f"Downloaded {download_url} to {destination}")
        return destination

    def clear_cache(self) -> None:
        if self._cache is not None:
            self._cache.invalidate(self.json_url)
