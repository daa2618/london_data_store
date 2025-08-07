from pathlib import Path
import sys
utils_dir = Path(__file__).resolve().parent/"utils"
if str(utils_dir) not in sys.path:
    sys.path.insert(0, str(utils_dir))
print(utils_dir)
print(sys.path)
from response import Response 
from strings_and_lists import ListOperations 
from logging_helper import BasicLogger #type:ignore
_bl = BasicLogger(verbose = False, log_directory=None,logger_name="LONDON_DATA_STORE")
from nltk.stem.snowball import SnowballStemmer
stemmer = SnowballStemmer("english")
import re
from itertools import chain
import datetime
from urllib.parse import urlsplit
import geopandas as gpd
import os


def _search_list_for_string(search_list, search_string):
    list_ops = ListOperations(search_list, search_string = search_string)
                                  
    filtered=list_ops.search_list_by_snowball()
    if filtered:
        return filtered
    else:
        filtered = list_ops.search_list_by_string_for_metric(0.5)
        if filtered:
            return filtered
        else:
            return None
        
class LondonDataStore:
    """
    Fetches and processes data from the London Open Data portal.

    This class combines data fetching capabilities (inheriting from `Response`) 
    with search term handling (inheriting from `SearchTerms`).  It retrieves a JSON 
    dataset from the specified URL, providing a foundation for further data analysis 
    and manipulation.

    Args:
        json_url (str, optional): The URL of the JSON dataset to retrieve. 
                                 Defaults to "https://data.london.gov.uk/api/datasets/export.json".
    """
    def __init__(self, json_url = "https://data.london.gov.uk/api/datasets/export.json"):
        self.json_url = json_url
        self._raw_response_json = None
        self._all_d_types = None
        
    def get_data_from_url(self):
        """Retrieves JSON data from a specified URL.

        This method fetches JSON data from the URL stored in the `self.json_url` attribute 
        using a `Response` object (assumed to be a custom class handling HTTP requests).  
        It then returns the parsed JSON data as a dictionary.

        Returns:
            dict: A dictionary containing the JSON data retrieved from the URL.  Returns None if there's an error during the fetch or parsing.

        Raises:
            Exception: Any exceptions raised during the HTTP request or JSON parsing are propagated.  Consider adding more specific exception handling if needed.
        """
        if self._raw_response_json is None:
            response_dict = Response(self.json_url).get_json_from_response()
            if not response_dict:
                return
            self._raw_response_json = response_dict
        return self._raw_response_json
    
    def get_all_slugs(self):
        """Retrieves a sorted list of unique slugs from data fetched from a URL.

        This function fetches data from a URL (using the `self.get_data_from_url()` method),
        extracts the "slug" attribute from each item, removes duplicate slugs using a set,
        and then sorts the resulting list of slugs alphabetically.

        Returns:
            list: A sorted list of unique slugs (strings).  Returns an empty list if no slugs are found or if `get_data_from_url()` returns an empty list or None.
        """
        
        slugs = list(set([x.get("slug") for x in self.get_data_from_url()]))
        slugs.sort()
        return slugs
    
    def filter_slugs_for_string(self, string):
        """Filters a list of slugs to retain only those containing a given string.

        This function utilizes the `filterListForString` method to filter a list 
        of slugs (obtained via `get_all_slugs()`) based on the presence of a specified 
        string.

        Args:
            string: The string to search for within the slugs.

        Returns:
            A list of slugs containing the input string.  Returns an empty list if no 
            slugs match or if an error occurs during filtering.
        """
        return _search_list_for_string(self.get_all_slugs(), string)
    
    def get_all_d_types(self):
        """Retrieves a unique list of data types from a collection of resources.

        This function fetches data from a URL (using a presumed `get_data_from_url` method), 
        extracts the 'format' field from each resource, and returns a unique set of these formats.

        Returns:
            list: A list of unique data types (strings representing formats). Returns an empty list if no data is found or if an error occurs during data retrieval/processing.
        """
        if self._all_d_types is None:
            try:
                dtypes = [[value.get("format") for key, value in x.get("resources").items()] for x in self.get_data_from_url()]
                dtypes = list(set(list(chain.from_iterable(dtypes))))
                self._all_d_types = dtypes
            except:
                self._all_d_types = []
        return self._all_d_types
    
    def filter_slug_for_d_type(self, req_format):
        """Filters a list of data resources to return only slugs matching a specified data type.

        Args:
            req_format: The required data format (e.g., "gpkg", "geojson").  
                    The function will automatically convert "gpkg" to "geopackage".

        Returns:
            A list of slugs corresponding to resources of the specified data type.

        Raises:
            ValueError: If the requested data type is not available or if no slugs are found 
                        for the requested data type.  The error message includes a list of 
                        available data types.
        """
        if req_format == "gpkg":
            req_format = "geopackage"
            
        if not req_format in self.get_all_d_types():
            raise ValueError(f"Available Data types: {', '.join(self.get_all_d_types())}")
        filtered = [y.get("slug") for y in self.get_data_from_url() if req_format in [x.get("format") for x in [value for key, value in y.get("resources").items()]]]
        if not filtered:
            raise ValueError("No slugs was found for the required data type")
        else:
            return filtered
        
    def get_download_url_for_slug(self, slug, get_description=False):
        """Retrieves download URLs for a given slug from a data source.

        This function fetches data from a URL (presumably containing metadata about downloadable resources), 
        finds entries matching the provided `slug`, and extracts download URLs for each matching entry.  
        It also provides information on when the data was last updated.

        Args:
            slug: The slug (identifier) to search for.
            get_description: A boolean flag. If True, the description of the matching data entry is printed. Defaults to False.

        Returns:
            A list of strings. Each string represents a download URL.  Returns an empty list if no matching slug is found.

        Prints:
            A message indicating when the data was last updated.  The format depends on the time elapsed.
            The number of URLs found.
            The description (if get_description is True).

        Notes:
            * This function relies on `self.get_data_from_url()` which return a list of dictionaries.  
            * Each dictionary should contain at least 'slug', 'updated_at', and 'resources' keys.  
            * The 'resources' key should contain a dictionary where each key is a resource identifier and 
            the value is a dictionary with at least a 'url' key.  
            * The function also utilizes URL parsing and manipulation via `urlsplit` and `Response.getBaseUrl()`.  
            * The date and time information is derived from the `updated_at` field (assumed to be an ISO format string).
        """
        urls = []
        for y in self.get_data_from_url():
            if y.get("slug") == slug:
                date = datetime.datetime.strftime(datetime.datetime.fromisoformat(y.get('updatedAt')), "%d %B %Y")
                data_time = datetime.datetime.fromisoformat(y.get("updatedAt"))
                tzinfo = data_time.tzinfo
                diff = datetime.datetime.now(tz=tzinfo) - data_time
                days = diff.days
                months = days // 30
                years = (days // 365)

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
                    #_bl.info(f"{key}/{value.get('searchFilename').replace(' ', '-')}")
                    
                    urls.append(f"{Response(self.json_url).get_base_url()}/download/{y.get('slug')}/{key}/{urlsplit(value.get('url')).path.split('/')[-1]}")
        _bl.info(f"{len(urls)} urls have been found. Choose relevant url.")
        return urls
    
    def filter_slugs_for_keyword(self, keyword):
        """Filters a list of slugs based on a keyword, using stemming for improved matching.

        This function retrieves data from a URL (presumably containing slugs and tags),
        stems the tags using a Porter stemmer (assumed to be defined as `stemmer`),
        and then filters the slugs to return only those whose associated tags contain 
        any of the stemmed words from the input keyword.

        Args:
            keyword: The keyword to search for in the tags.  This will be broken down into individual words.

        Returns:
            A list of slugs (strings) where the associated tags contain any stemmed version of a word from the keyword.  Returns an empty list if no matches are found or if an error occurs during data retrieval.

        Notes:
            - This function relies on `self.get_data_from_url()` to retrieve data, and `self.getListOfWords()` to split the keyword into words.
            - The stemming process improves matching by reducing words to their root form (e.g., "running" becomes "run").
            - Error handling (e.g., handling exceptions from `get_data_from_url()`) is not explicitly included but is recommended for production code.
    """
        #slugs = []
        search_terms = [stemmer.stem(x) for x in re.sub("[-_]", " ", keyword.rstrip(" ").lstrip(" ").lower()).split(" ")]
        slugs = [x.get("slug") for x in self.get_data_from_url() \
                 if any(word in y for y in \
                        [stemmer.stem(z) for z in x.get("tags")] \
                            for word in search_terms)]
        return slugs
    
    def get_map_data_to_plot(self, slug, extension):
        """Retrieves and processes map data for plotting.

        This function retrieves map data associated with a given slug and file extension,
        processes it (including setting and transforming the coordinate reference system),
        and returns the data as a GeoDataFrame or a list of URLs if multiple files exist.

        Args:
            slug (str): The slug identifying the map data.
            extension (str): The file extension of the desired map data (e.g., "geojson", "gpkg", "shp").  Accepts "geopackage" as an alias for "gpkg".

        Returns:
            geopandas.GeoDataFrame or list: A GeoDataFrame containing the map data in EPSG:4326 projection if a single file is found.  Returns a list of URLs if multiple files match the given slug and extension.

        Raises:
            TypeError: If the provided extension is not one of "geojson", "gpkg", or "shp".
            ValueError: If no map data is found for the given slug and extension.  Provides suggestions based on available extensions.
        """
        map_types = {"geojson","gpkg","shp"}
        
        if extension == "geopackage":
            extension = "gpkg"
            
        if extension not in map_types:
            #raise ValueError(f"The given slug '{slug}' does not have any map data associated with it")
            raise TypeError(f"Extension for map data should be one of {map_types}")
        
        urls = self.get_download_url_for_slug(slug=slug)
        ext_for_slug = [x for x in set([os.path.splitext(x)[1] for x in urls]) if x != ""]
        
        urls = [x for x in urls if x.endswith(extension)]
        
        if not urls:
            raise ValueError(f"The given slug '{slug}' does not have any map data associated with it\nTry extensions from {ext_for_slug}")
            
        elif len(urls) == 1:
            url = urls[0]
            
            dat = gpd.read_file(url)

            if dat.crs.to_epsg() is None:
                dat.set_crs(crs="EPSG:27700", allow_override=True, inplace=True)

            dat.to_crs(crs="EPSG:4326", inplace=True)
            return dat
        else:
            return urls