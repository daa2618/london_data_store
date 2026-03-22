import datetime
import os
import re
import warnings
from collections.abc import Callable
from itertools import chain
from pathlib import Path
from urllib.parse import urlsplit

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .cache import CatalogueCache
from .download import DownloadManager
from .exceptions import DatasetNotFoundError, FormatNotAvailableError
from .models import Dataset
from .utils.logging_helper import BasicLogger
from .utils.response import Response
from .utils.strings_and_lists import ListOperations

_bl = BasicLogger(verbose=False, log_directory=None, logger_name="LONDON_DATA_STORE")

_stemmer = None


def _get_stemmer():
    global _stemmer
    if _stemmer is None:
        from nltk.stem.snowball import SnowballStemmer

        _stemmer = SnowballStemmer("english")
    return _stemmer


def _search_list_for_string(search_list: list[str], search_string: str) -> list[str] | None:
    list_ops = ListOperations(search_list, search_string=search_string)

    filtered = list_ops.search_list_by_snowball()
    if filtered:
        return filtered
    else:
        filtered = list_ops.search_list_by_string_for_metric(0.5)
        if filtered:
            return filtered
        else:
            return None


def _validate_string(value: object, param_name: str = "parameter") -> str:
    """Validate that a value is a non-empty string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"'{param_name}' must be a non-empty string, got: {value!r}")
    return value.strip()


class LondonDataStore:
    """
    Fetches and processes data from the London Open Data portal.

    Uses the portal's JSON export API to discover datasets, filter by format
    or keyword, and resolve download URLs. Supports spatial data via GeoPandas.

    Args:
        json_url (str, optional): The URL of the JSON dataset to retrieve.
                                 Defaults to "https://data.london.gov.uk/api/datasets/export.json".
    """

    def __init__(
        self,
        json_url: str = "https://data.london.gov.uk/api/v2/datasets/export.json",
        cache: bool = True,
        cache_ttl: int = 86400,
        cache_dir: Path | None = None,
    ):
        self.json_url = json_url
        self._raw_response_json = None
        self._all_d_types = None
        self._base_url = None
        self._cache = CatalogueCache(cache_dir=cache_dir, ttl_seconds=cache_ttl) if cache else None

        # Shared session with automatic retries
        self._session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry)
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self._session.close()

    def __enter__(self) -> "LondonDataStore":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    @property
    def base_url(self) -> str:
        """Base URL (scheme://netloc) derived from json_url, computed once."""
        if self._base_url is None:
            parts = urlsplit(self.json_url)
            self._base_url = f"{parts.scheme}://{parts.netloc}"
        return self._base_url

    def get_data_from_url(self) -> list[dict] | None:
        """Retrieves JSON data from a specified URL.

        Checks disk cache first (if caching is enabled). On cache miss,
        fetches from the network and caches the result.

        Returns:
            dict: The JSON data retrieved from the URL, or None on error.

        """
        if self._raw_response_json is None:
            # Try cache first
            if self._cache is not None:
                cached = self._cache.get(self.json_url)
                if cached is not None:
                    self._raw_response_json = cached
                    return self._raw_response_json

            response_dict = Response(self.json_url, session=self._session).get_json_from_response()
            if not response_dict:
                return
            self._raw_response_json = response_dict

            # Store in cache
            if self._cache is not None:
                self._cache.put(self.json_url, response_dict)
        return self._raw_response_json

    def clear_cache(self) -> None:
        """Invalidate the cached catalogue for this instance's URL."""
        if self._cache is not None:
            self._cache.invalidate(self.json_url)

    def get_all_slugs(self) -> list[str]:
        """Retrieves a sorted list of unique slugs from data fetched from a URL.

        This function fetches data from a URL (using the `self.get_data_from_url()` method),
        extracts the "slug" attribute from each item, removes duplicate slugs using a set,
        and then sorts the resulting list of slugs alphabetically.

        Returns:
            list: A sorted list of unique slug strings.
        """

        slugs = list(set([x.get("slug") for x in self.get_data_from_url()]))
        slugs.sort()
        return slugs

    def filter_slugs_for_string(self, string: str) -> list[str] | None:
        """Filters a list of slugs to retain only those containing a given string.

        .. deprecated:: 0.2.0
            Use :meth:`search` instead, which returns scored results.

        Args:
            string: The string to search for within the slugs.

        Returns:
            A list of slugs containing the input string.  Returns None if no
            slugs match.
        """
        warnings.warn(
            "filter_slugs_for_string() is deprecated, use search() for scored results",
            DeprecationWarning,
            stacklevel=2,
        )
        _validate_string(string, "string")
        return _search_list_for_string(self.get_all_slugs(), string)

    def get_all_d_types(self) -> list[str]:
        """Retrieves a unique list of data types from a collection of resources.

        Returns:
            list: A list of unique data type strings. Empty list on error.
        """
        if self._all_d_types is None:
            try:
                dtypes = [
                    [value.get("format") for key, value in x.get("resources").items()] for x in self.get_data_from_url()
                ]
                dtypes = list(set(list(chain.from_iterable(dtypes))))
                self._all_d_types = dtypes
            except (AttributeError, TypeError):
                self._all_d_types = []
        return self._all_d_types

    def filter_slug_for_d_type(self, req_format: str) -> list[str]:
        """Filters a list of data resources to return only slugs matching a specified data type.

        Args:
            req_format: The required data format (e.g., "gpkg", "geojson").
                    The function will automatically convert "gpkg" to "geopackage".

        Returns:
            A list of slugs corresponding to resources of the specified data type.

        Raises:
            ValueError: If the requested data type is not available or if no slugs are found
                        for the requested data type.
        """
        if req_format == "gpkg":
            req_format = "geopackage"

        if req_format not in self.get_all_d_types():
            raise FormatNotAvailableError(f"Available Data types: {', '.join(self.get_all_d_types())}")
        filtered = [
            y.get("slug")
            for y in self.get_data_from_url()
            if req_format in [x.get("format") for x in [value for key, value in y.get("resources").items()]]
        ]
        if not filtered:
            raise FormatNotAvailableError("No slugs was found for the required data type")
        else:
            return filtered

    def get_download_url_for_slug(self, slug: str, get_description: bool = False) -> list[str]:
        """Retrieves download URLs for a given slug from a data source.

        Args:
            slug: The slug (identifier) to search for.
            get_description: If True, log the dataset description. Defaults to False.

        Returns:
            A list of download URL strings. Empty list if no matching slug.
        """
        _validate_string(slug, "slug")
        urls = []
        for y in self.get_data_from_url():
            if y.get("slug") == slug:
                date = datetime.datetime.strftime(datetime.datetime.fromisoformat(y.get("updatedAt")), "%d %B %Y")
                data_time = datetime.datetime.fromisoformat(y.get("updatedAt"))
                tzinfo = data_time.tzinfo
                diff = datetime.datetime.now(tz=tzinfo) - data_time
                days = diff.days
                months = days // 30
                years = days // 365

                updated_at = []
                if days <= 30:
                    updated_at.append(f"{days} days")
                elif months <= 12:
                    updated_at.append(f"{months} months")
                else:
                    updated_at.append(f"{years} years")
                _bl.info(f"The data was last updated '{updated_at[0]}' ago on '{date}'")

                if get_description:
                    _bl.info(y.get("description"))
                for key, value in y.get("resources").items():
                    urls.append(
                        f"{self.base_url}/download/{y.get('slug')}/{key}/{urlsplit(value.get('url')).path.split('/')[-1]}"
                    )
        _bl.info(f"{len(urls)} urls have been found. Choose relevant url.")
        return urls

    def filter_slugs_for_keyword(self, keyword: str) -> list[str]:
        """Filters a list of slugs based on a keyword, using stemming for improved matching.

        Args:
            keyword: The keyword to search for in the tags. Broken down into individual words.

        Returns:
            A list of matching slug strings. Empty list if no matches.
        """
        _validate_string(keyword, "keyword")
        stemmer = _get_stemmer()
        search_terms = [stemmer.stem(x) for x in re.sub("[-_]", " ", keyword.strip().lower()).split(" ")]
        slugs = [
            x.get("slug")
            for x in self.get_data_from_url()
            if any(word in y for y in [stemmer.stem(z) for z in x.get("tags")] for word in search_terms)
        ]
        return slugs

    def get_map_data_to_plot(self, slug: str, extension: str):
        """Retrieves and processes map data for plotting.

        Args:
            slug (str): The slug identifying the map data.
            extension (str): File extension ("geojson", "gpkg", "shp"). Accepts "geopackage" as alias.

        Returns:
            GeoDataFrame in EPSG:4326 if single file found, or list of URLs if multiple.

        Raises:
            TypeError: If the provided extension is not one of "geojson", "gpkg", or "shp".
            ValueError: If no map data is found for the given slug and extension.
            ImportError: If geopandas is not installed.
        """
        _validate_string(slug, "slug")
        _validate_string(extension, "extension")

        map_types = {"geojson", "gpkg", "shp"}

        if extension == "geopackage":
            extension = "gpkg"

        if extension not in map_types:
            raise TypeError(f"Extension for map data should be one of {map_types}")

        urls = self.get_download_url_for_slug(slug=slug)
        ext_for_slug = [x for x in set([os.path.splitext(x)[1] for x in urls]) if x != ""]

        urls = [x for x in urls if x.endswith(extension)]

        if not urls:
            raise DatasetNotFoundError(
                f"The given slug '{slug}' does not have any map data associated with it\n"
                f"Try extensions from {ext_for_slug}"
            )

        if len(urls) != 1:
            return urls

        try:
            import geopandas as gpd
        except ImportError:
            raise ImportError(
                "geopandas is required for spatial data. Install it with: pip install london-data-store[geo]"
            ) from None

        dat = gpd.read_file(urls[0])

        if dat.crs.to_epsg() is None:
            dat = dat.set_crs(crs="EPSG:27700", allow_override=True)

        dat = dat.to_crs(crs="EPSG:4326")
        return dat

    # ── v2 methods ─────────────────────────────────────────────────

    def search(self, term: str, limit: int = 20) -> list[tuple[str, float]]:
        """Search slugs by term, returning (slug, score) pairs sorted by score descending.

        Uses SequenceMatcher similarity scoring against all slugs.

        Args:
            term: The search term.
            limit: Maximum number of results to return.

        Returns:
            A list of (slug, score) tuples sorted by score descending.
        """
        _validate_string(term, "term")
        list_ops = ListOperations(self.get_all_slugs(), search_string=term)
        scored = list_ops.search_list_with_scores()
        return scored[:limit]

    def get_dataset(self, slug: str) -> Dataset:
        """Return a fully-populated Dataset model for the given slug.

        Args:
            slug: The dataset slug identifier.

        Returns:
            A Dataset instance with all available fields populated.

        Raises:
            DatasetNotFoundError: If no dataset matches the slug.
        """
        _validate_string(slug, "slug")
        for item in self.get_data_from_url():
            if item.get("slug") == slug:
                return Dataset.from_api_dict(item)
        raise DatasetNotFoundError(f"Dataset with slug '{slug}' not found")

    def get_all_topics(self) -> list[str]:
        """Return a sorted list of all unique topic categories in the catalogue.

        Returns:
            A sorted list of topic strings.
        """
        topics = set()
        for item in self.get_data_from_url():
            for topic in item.get("topics", []):
                topics.add(topic)
        return sorted(topics)

    def filter_by_topic(self, topic: str) -> list[str]:
        """Return slugs of datasets tagged with the given topic.

        Args:
            topic: The topic category to filter by.

        Returns:
            A list of matching slug strings.
        """
        _validate_string(topic, "topic")
        return [x.get("slug") for x in self.get_data_from_url() if topic in x.get("topics", [])]

    def filter_by_publisher(self, publisher: str) -> list[str]:
        """Return slugs where publisher matches (case-insensitive substring).

        Args:
            publisher: The publisher name or substring to match.

        Returns:
            A list of matching slug strings.
        """
        _validate_string(publisher, "publisher")
        publisher_lower = publisher.lower()
        return [
            x.get("slug") for x in self.get_data_from_url() if publisher_lower in (x.get("publisher") or "").lower()
        ]

    def filter_by_update_frequency(self, frequency: str) -> list[str]:
        """Return slugs with the given update frequency.

        Args:
            frequency: The update frequency string (e.g., 'Monthly', 'Annual', 'One off').

        Returns:
            A list of matching slug strings.
        """
        _validate_string(frequency, "frequency")
        frequency_lower = frequency.lower()
        return [
            x.get("slug")
            for x in self.get_data_from_url()
            if frequency_lower == (x.get("custom", {}).get("update_frequency") or "").lower()
        ]

    def filter_by_licence(self, licence_keyword: str) -> list[str]:
        """Return slugs whose licence title contains the keyword.

        Args:
            licence_keyword: A keyword to search for in licence titles.

        Returns:
            A list of matching slug strings.
        """
        _validate_string(licence_keyword, "licence_keyword")
        keyword_lower = licence_keyword.lower()
        return [
            x.get("slug")
            for x in self.get_data_from_url()
            if keyword_lower in (x.get("licence", {}).get("title") or "").lower()
        ]

    def download_file(
        self,
        slug: str,
        format: str | None = None,
        destination: str | Path = ".",
        *,
        resource_key: str | None = None,
        progress_callback: Callable[[int, int | None], None] | None = None,
        verify_integrity: bool = True,
    ) -> Path:
        """Download a resource file for the given dataset slug.

        If format is specified, downloads the first matching resource.
        If resource_key is specified, downloads that exact resource.
        Destination can be a directory (filename inferred) or a full path.

        Args:
            slug: The dataset slug.
            format: File format to match (e.g., 'csv', 'geojson'). Downloads first match.
            destination: Target path (directory or file). Defaults to current directory.
            resource_key: Specific resource key to download.
            progress_callback: Called with (bytes_downloaded, total_bytes) after each chunk.
            verify_integrity: If True, verify hash and size from resource metadata.

        Returns:
            The final file path.

        Raises:
            DatasetNotFoundError: If slug not found.
            FormatNotAvailableError: If format not found for slug.
            DownloadError: On download or integrity failure.
        """
        _validate_string(slug, "slug")
        dataset = self.get_dataset(slug)

        # Find the matching resource
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

        # Build download URL
        url_path = urlsplit(resource.url).path.split("/")[-1]
        download_url = f"{self.base_url}/download/{slug}/{resource.key}/{url_path}"

        # Prepare integrity check params
        expected_hash = resource.check_hash if verify_integrity else None
        expected_size = resource.check_size if verify_integrity else None

        manager = DownloadManager(self._session)
        return manager.download_file(
            url=download_url,
            destination=Path(destination),
            progress_callback=progress_callback,
            expected_hash=expected_hash,
            expected_size=expected_size,
        )
