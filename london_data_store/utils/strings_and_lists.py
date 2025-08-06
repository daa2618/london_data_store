from difflib import SequenceMatcher
from nltk.stem.snowball import SnowballStemmer
import itertools
import numpy as np, re
import sys

from pathlib import Path
from .logging_helper import BasicLogger

_bl = BasicLogger(verbose=False, log_directory=None, logger_name="STRINGS AND LISTS")

stemmer = SnowballStemmer("english")

class ConversionError(Exception):
    pass


class StringOperations:
    """
    A class for performing various operations on a given string.

    Args:
        string (str): The input string on which operations will be performed.
    """
    def __init__(self, string:str):
        self.string = string
        pass

    def _convert_string_to_numbers(self, d_type:str, notations = dict(K=1000, M=1000000)) -> (int|float):
        """Converts a string containing a number (potentially with suffixes like 'K' or 'M') to an integer or float.

        Args:
            d_type (str): The desired data type of the output ('integer' or 'float').

        Returns:
            int or float: The converted number.

        Raises:
            ConversionError: If the input string cannot be converted to a number, 
                             if multiple numbers are found, or if the specified data type is invalid.  
                             Error messages provide details about the failure.
        """
        string_number=str(self.string)
        #if string_number == "0":
         #   number = float(string_number)
        #else:
            #_bl.info(string_number)
        
        number = re.findall("\\d+\\.?\\d*", re.sub(",", "", string_number))
        if not number:
            raise ConversionError(f"Extraction of numbers from '{string_number}' failed: Result '{number}'")
        try:
            number = ListOperations(number).get_single_result_dict()
        except:
            number = None
        
        if not number:
            raise ConversionError("Unique object could not be extracted from the numbers list")
        try:
            number = float(number)
        except Exception as e:
            raise ConversionError(f"'{number}' could not be converted to float")
            
        for end in notations.keys():
            if string_number.endswith(end):
                number = number * notations.get(end)
        if d_type == "integer":
            return int(number)
        elif d_type == "float":
            return float(number)
    
    def convert_to_integer(self):
        """Converts a string containing a number (potentially with suffixes like 'K' or 'M') to an integer.


        Returns:
            int : The converted number.

        Raises:
            ConversionError: If the input string cannot be converted to a number, 
                             if multiple numbers are found, or if the specified data type is invalid.  
                             Error messages provide details about the failure.
        """
        return self._convert_string_to_numbers("integer")

    def convert_to_float(self):
        """Converts a string containing a number (potentially with suffixes like 'K' or 'M') to a float.


        Returns:
            float : The converted number.

        Raises:
            ConversionError: If the input string cannot be converted to a number, 
                             if multiple numbers are found, or if the specified data type is invalid.  
                             Error messages provide details about the failure.
        """
        return self._convert_string_to_numbers("float")


class ClassIntiationError(Exception):
    pass

class ListOperations:
    """
    Class to search a list with strings by matching a search string and get matching results
    by various string operations and modules like SnowballStemmer, SequenceMatcher


    """
    def __init__(self, search_list:list, **kwargs):
        """Initiate StringsListOperations class

        Args:
            search_list (list): A list of strings to compare against.
        Kwargs:
            search_string (str): The string to compare each string in search_list against.
        """
        self.search_list = list(search_list) if isinstance(search_list, (set, dict)) else search_list 
        self._search_string = kwargs.get("search_string")
    
    @property
    def search_string(self):
        """Search String property"""
        if self._search_string is None or self._search_string == "":
            raise ClassIntiationError("Initiate class by assinging 'search_string' as kwargs")
        return self._search_string
    
    @search_string.setter
    def search_string(self, value):
        _bl.info("search_string was set")
        self._search_string = value
    

    def _get_matching_scores_for_string(self):
        """Calculates the similarity ratio between a string and a list of strings.

        This function iterates through a list of strings and computes the similarity ratio 
        of each string to a specified string using the SequenceMatcher.ratio() method.  
        The comparison is case-insensitive.  Empty strings in the input list are ignored.

        Returns:
            A list of floats. Each float represents the similarity ratio (between 0 and 1 inclusive) 
            of a string from search_list to search_string.  The order of ratios corresponds to 
            the order of strings in search_list (excluding empty strings).  Returns an empty list if 
            search_list is empty or contains only empty strings.
        """
        return [SequenceMatcher(None, x.lower(), self.search_string.lower()).ratio() \
                for x in self.search_list if x]

    
    def get_best_matching_string(self) -> str:
        """
        Finds the string in a list that has the highest similarity ratio to a given string.


        Returns:
            str: The string from the list with the highest similarity ratio to search_string.  Returns None if the list is empty.

        Note:
            Similarity is determined using the `SequenceMatcher` from the `difflib` library, comparing lowercased versions of the strings.  The function returns only the *best* match, not a list of matches ranked by similarity.
        """
        matching_ratios=self._get_matching_scores_for_string()
        return self.search_list[matching_ratios.index(max(matching_ratios))]
    
    
    def search_list_by_snowball(self):
        """Searches a list of strings using the Snowball stemmer.

        This function filters a list of strings, retaining only those that contain the stemmed version of a given search string.  It uses the Snowball stemmer (assumed to be defined globally as `stemmer`) for stemming both the search string and the strings in the list.

        Returns:
            A list containing the strings from `search_list` that contain the stemmed `search_string`, or None if no matches are found.
        """
        filtered=[x for x in self.search_list \
                  if x and stemmer.stem(self.search_string) in stemmer.stem(x)]
        if filtered:
            return filtered
        else:
            return None
        
    def search_list_by_string_for_metric(self, search_metric:float|str):
        
        """Searches a list based on a metric applied to matching scores derived from strings.

        This function retrieves matching scores from a string, and then filters 
        the main search list (`self.search_list`) based on the provided `search_metric`.  The metric can be:

        - A float:  Items with matching scores greater than or equal to this float are retained.
        - A string:  "mean", "median", "0.25", "0.75", or "0.5".  Items with matching scores greater than 
            or equal to the respective mean, median, or quantile (25th, 75th, or 50th percentile) are retained.

        Args:
            search_metric (float | str): The metric to use for filtering.  Can be a float, "mean", "median", "0.25", "0.75", or "0.5".

        Returns:
            list: A list containing the filtered items from `self.search_list` that meet the specified criteria. 
                Returns None if no matching results are found, printing a message to the console.

        Raises:
            None.  Handles invalid string inputs gracefully by returning None.  Note that errors in `_get_matching_scores_for_string` are not explicitly handled here.
        """
        matching_scores = self._get_matching_scores_for_string()
        str_metrics = ["mean", "mode", "median", "0.25", "0.75", "0.5"]
        
        if search_metric in str_metrics:
            if search_metric == "mean":
                score_indexes=[True if x >= np.mean(matching_scores) else False for x in matching_scores]
            elif search_metric == "median":
                score_indexes=[True if x >= np.median(matching_scores) else False for x in matching_scores]
            elif search_metric == "mode":
                mode = max(set(matching_scores), key=matching_scores.count)
                score_indexes=[True if x >=mode else False for x in matching_scores]
            elif search_metric in ["0.25", "0.75", "0.5"]:
                q=float(search_metric)
                score_indexes=[True if x >= np.quantile(matching_scores, q) else False for x in matching_scores]
        else:
            try:
                search_metric=float(search_metric)
            except:
                pass

            if isinstance(search_metric, float):
                score_indexes=[True if x >= search_metric else False for x in matching_scores]
        
            

        filtered=[self.search_list[x] for x in list(itertools.compress(range(len(score_indexes)),
                                                                    score_indexes))]
        if filtered:
            return filtered
        else:
            _bl.warning("No matching results was found for given search metric\nConsider reducing the value")
            return None
    

    def get_unique_sorted_elements(self)->list:
        """Returns a sorted list of unique elements from the input list.

        Returns:
            A new list containing only the unique elements from search List, 
            sorted in ascending order.

        Raises:
            ValueError: If the input list is empty.
        """
        if self.search_list:
            search_list = [x for x in self.search_list if x]

            if any(isinstance(x, list) for x in search_list):
                unique_elems = list(set(itertools.chain.from_iterable(search_list)))
            else:
                unique_elems = list(set(search_list))
            unique_elems = [x for x in unique_elems if x]
            unique_elems.sort()
            return unique_elems
        else:
            raise ValueError("List should not be empty")
    
    def get_unique_sorted_elements_by_key(self, id_key:str, sort_key:str=None)->list:
        """
    Extracts a list of unique dictionaries from a list of dictionaries,
    where uniqueness is determined by the value of a specified key, and
    optionally sorts the resulting list by another specified key.

    Args:
        id_key (str): The key used to identify unique elements.
                     Only the first occurrence of an element with a given
                     value for this key will be included in the result.
        sort_key (str, optional): The key used to sort the unique elements.
                                  If provided, the result will be sorted in ascending
                                  order based on the values associated with this key.
                                  Defaults to None (no sorting).

    Returns:
        list: A list of unique dictionaries, optionally sorted by the 'sort_key'.

    Raises:
        KeyError: If either the `id_key` or the `sort_key` (if provided) are not
                  present as keys in the dictionaries within the `self.search_list`.
        ClassIntiationError: If `self.search_list` is empty.

    Examples:
        Assume self.search_list is:
        [
            {'id': 1, 'name': 'apple', 'order': 2},
            {'id': 2, 'name': 'banana', 'order': 1},
            {'id': 1, 'name': 'apple', 'order': 3},
            {'id': 3, 'name': 'cherry', 'order': 4}
         ]

        >>> # get_unique_sorted_elements_by_key(self, 'id')
        [
           {'id': 1, 'name': 'apple', 'order': 2},
           {'id': 2, 'name': 'banana', 'order': 1},
           {'id': 3, 'name': 'cherry', 'order': 4}
        ]


        >>> # get_unique_sorted_elements_by_key(self, 'id', 'name')
        [
           {'id': 1, 'name': 'apple', 'order': 2},
           {'id': 2, 'name': 'banana', 'order': 1},
           {'id': 3, 'name': 'cherry', 'order': 4}
        ]

        >>> # get_unique_sorted_elements_by_key(self, 'id', 'order')
        [
           {'id': 2, 'name': 'banana', 'order': 1},
           {'id': 1, 'name': 'apple', 'order': 2},
           {'id': 3, 'name': 'cherry', 'order': 4}
        ]

    """
        unique_list = []
        keys = []
        if self.search_list:
            for key in [id_key, sort_key]:
                if key and key not in self.search_list[0].keys():
                    raise KeyError(f"'{key}' not found. Available keys: {', '.join(self.search_list[0].keys())}")
            
            for x in self.search_list:
                title = x.get(id_key)
                if title not in keys:
                    keys.append(title)
                    unique_list.append(x)
            
            if sort_key:
                key = lambda x: x.get(sort_key)
                unique_list.sort(key=key)
            return unique_list
        
        else:
            raise ClassIntiationError()
    
    def get_single_result_dict(self):
        """
        Retrieves a single dictionary from a list of dictionaries, ensuring uniqueness.

        This function checks if the internal `self.search_list` contains exactly one
        dictionary. If it does, the function returns that dictionary. If the list is
        empty, or contains more than one dictionary, a `ValueError` is raised.

        Returns:
            dict: The single dictionary from `self.search_list` if it contains exactly one element.

        Raises:
            ValueError:
                - If `self.search_list` is empty.
                - If `self.search_list` contains more than one dictionary.

        Examples:
            Assume self.search_list is:
            - `[{'key': 'value'}]`

            >>> # get_single_result_dict(self)
            {'key': 'value'}

            Assume self.search_list is:
            - `[]`

            >>> # get_single_result_dict(self)
            ValueError("No matching results")

            Assume self.search_list is:
            -   `[{'key1': 'value1'}, {'key2': 'value2'}]`

            >>> # get_single_result_dict(self)
            ValueError("More than one matching results")

        """
        if self.search_list:
            if len(self.search_list)==1:
                return self.search_list[0]
            else:
                raise ValueError("More than one matching results")
        else:
            raise ValueError("No matching results")
        

    
    
    