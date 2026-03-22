import datetime
import os
import re
from itertools import chain
from urllib.parse import urlsplit

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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

    def __init__(self, json_url: str = "https://data.london.gov.uk/api/datasets/export.json"):
        self.json_url = json_url
        self._raw_response_json = None
        self._all_d_types = None
        self._base_url = None

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

        This method fetches JSON data from the URL stored in the `self.json_url` attribute
        using a `Response` object (assumed to be a custom class handling HTTP requests).
        It then returns the parsed JSON data as a dictionary.

        Returns:
            dict: The JSON data retrieved from the URL, or None on error.

        """
        if self._raw_response_json is None:
            response_dict = Response(self.json_url, session=self._session).get_json_from_response()
            if not response_dict:
                return
            self._raw_response_json = response_dict
        return self._raw_response_json

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

        Args:
            string: The string to search for within the slugs.

        Returns:
            A list of slugs containing the input string.  Returns None if no
            slugs match.
        """
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
            raise ValueError(f"Available Data types: {', '.join(self.get_all_d_types())}")
        filtered = [
            y.get("slug")
            for y in self.get_data_from_url()
            if req_format in [x.get("format") for x in [value for key, value in y.get("resources").items()]]
        ]
        if not filtered:
            raise ValueError("No slugs was found for the required data type")
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
        try:
            import geopandas as gpd
        except ImportError:
            raise ImportError(
                "geopandas is required for spatial data. Install it with: pip install london-data-store[geo]"
            ) from None

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
            raise ValueError(
                f"The given slug '{slug}' does not have any map data associated with it\n"
                f"Try extensions from {ext_for_slug}"
            )

        elif len(urls) == 1:
            url = urls[0]

            dat = gpd.read_file(url)

            if dat.crs.to_epsg() is None:
                dat = dat.set_crs(crs="EPSG:27700", allow_override=True)

            dat = dat.to_crs(crs="EPSG:4326")
            return dat
        else:
            return urls
