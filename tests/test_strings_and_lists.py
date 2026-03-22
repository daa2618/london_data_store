"""Tests for london_data_store.utils.strings_and_lists module."""

import pytest

from london_data_store.utils.strings_and_lists import (
    ClassInitiationError,
    ClassIntiationError,
    ConversionError,
    ListOperations,
    StringOperations,
)

# ── StringOperations ──────────────────────────────────────────────


class TestConvertToInteger:
    def test_plain_number(self):
        assert StringOperations("42").convert_to_integer() == 42

    def test_number_with_k_suffix(self):
        assert StringOperations("1.5K").convert_to_integer() == 1500

    def test_number_with_m_suffix(self):
        assert StringOperations("2M").convert_to_integer() == 2000000

    def test_number_with_commas(self):
        assert StringOperations("1,234").convert_to_integer() == 1234

    def test_number_embedded_in_text(self):
        assert StringOperations("about 100 people").convert_to_integer() == 100

    def test_no_number_raises(self):
        with pytest.raises(ConversionError):
            StringOperations("no numbers here").convert_to_integer()

    def test_multiple_numbers_raises(self):
        with pytest.raises(ConversionError):
            StringOperations("10 to 20").convert_to_integer()


class TestConvertToFloat:
    def test_plain_float(self):
        assert StringOperations("3.14").convert_to_float() == 3.14

    def test_float_with_k_suffix(self):
        assert StringOperations("1.2K").convert_to_float() == 1200.0

    def test_integer_string_as_float(self):
        assert StringOperations("5").convert_to_float() == 5.0


# ── ListOperations ────────────────────────────────────────────────


class TestSearchString:
    def test_search_string_required(self):
        lo = ListOperations(["a", "b"])
        with pytest.raises(ClassIntiationError):
            _ = lo.search_string

    def test_search_string_settable(self):
        lo = ListOperations(["a", "b"])
        lo.search_string = "test"
        assert lo.search_string == "test"

    def test_backward_compatible_alias(self):
        assert ClassInitiationError is ClassIntiationError


class TestSearchListBySnowball:
    def test_exact_match(self):
        lo = ListOperations(["cycling journeys", "bus usage"], search_string="cycling")
        result = lo.search_list_by_snowball()
        assert result == ["cycling journeys"]

    def test_stemmed_match(self):
        lo = ListOperations(["cycling journeys", "bus usage"], search_string="cycle")
        result = lo.search_list_by_snowball()
        assert result == ["cycling journeys"]

    def test_no_match(self):
        lo = ListOperations(["apple", "banana"], search_string="zebra")
        result = lo.search_list_by_snowball()
        assert result is None

    def test_empty_strings_skipped(self):
        lo = ListOperations(["", "hello world", ""], search_string="hello")
        result = lo.search_list_by_snowball()
        assert result == ["hello world"]


class TestGetBestMatchingString:
    def test_best_match(self):
        lo = ListOperations(["apple", "application", "banana"], search_string="app")
        result = lo.get_best_matching_string()
        assert result in ["apple", "application"]  # either is valid


class TestSearchByMetric:
    def test_float_threshold(self):
        lo = ListOperations(["hello", "help", "world"], search_string="helo")
        result = lo.search_list_by_string_for_metric(0.5)
        assert "hello" in result
        assert "world" not in result

    def test_mean_metric(self):
        lo = ListOperations(["hello", "help", "world"], search_string="helo")
        result = lo.search_list_by_string_for_metric("mean")
        assert isinstance(result, list)

    def test_median_metric(self):
        lo = ListOperations(["hello", "help", "world"], search_string="helo")
        result = lo.search_list_by_string_for_metric("median")
        assert isinstance(result, list)

    def test_quantile_metric(self):
        lo = ListOperations(["hello", "help", "world", "hex"], search_string="helo")
        result = lo.search_list_by_string_for_metric("0.75")
        assert isinstance(result, list)

    def test_high_threshold_returns_none(self):
        lo = ListOperations(["apple", "banana"], search_string="xyz")
        result = lo.search_list_by_string_for_metric(0.99)
        assert result is None


class TestGetUniqueSortedElements:
    def test_unique_sorted(self):
        lo = ListOperations(["banana", "apple", "banana", "cherry"])
        result = lo.get_unique_sorted_elements()
        assert result == ["apple", "banana", "cherry"]

    def test_empty_list_raises(self):
        lo = ListOperations([])
        with pytest.raises(ValueError):
            lo.get_unique_sorted_elements()

    def test_nested_lists_flattened(self):
        lo = ListOperations([["a", "b"], ["b", "c"]])
        result = lo.get_unique_sorted_elements()
        assert result == ["a", "b", "c"]

    def test_none_values_filtered(self):
        lo = ListOperations(["a", None, "b", None])
        result = lo.get_unique_sorted_elements()
        assert result == ["a", "b"]


class TestGetUniqueSortedElementsByKey:
    def test_unique_by_id(self):
        data = [
            {"id": 1, "name": "apple"},
            {"id": 2, "name": "banana"},
            {"id": 1, "name": "apple duplicate"},
        ]
        lo = ListOperations(data)
        result = lo.get_unique_sorted_elements_by_key("id")
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[1]["id"] == 2

    def test_sorted_by_key(self):
        data = [
            {"id": 1, "name": "cherry", "order": 3},
            {"id": 2, "name": "apple", "order": 1},
            {"id": 3, "name": "banana", "order": 2},
        ]
        lo = ListOperations(data)
        result = lo.get_unique_sorted_elements_by_key("id", sort_key="order")
        assert result[0]["order"] == 1

    def test_missing_key_raises(self):
        data = [{"id": 1, "name": "apple"}]
        lo = ListOperations(data)
        with pytest.raises(KeyError):
            lo.get_unique_sorted_elements_by_key("missing_key")

    def test_empty_list_raises(self):
        lo = ListOperations([])
        with pytest.raises(ClassIntiationError):
            lo.get_unique_sorted_elements_by_key("id")


class TestGetSingleResultDict:
    def test_single_element(self):
        lo = ListOperations(["only_one"])
        assert lo.get_single_result_dict() == "only_one"

    def test_empty_raises(self):
        lo = ListOperations([])
        with pytest.raises(ValueError, match="No matching results"):
            lo.get_single_result_dict()

    def test_multiple_raises(self):
        lo = ListOperations(["a", "b"])
        with pytest.raises(ValueError, match="More than one"):
            lo.get_single_result_dict()
