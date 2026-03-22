"""Tests for london_data_store.utils.response module."""

import json
from unittest.mock import MagicMock, patch

import pytest

from london_data_store.utils.response import GET_RESPONSE, POST_RESPONSE, MethodError, Response


class TestGetBaseUrl:
    def test_https_url(self):
        r = Response("https://data.london.gov.uk/api/datasets/export.json")
        assert r.get_base_url() == "https://data.london.gov.uk"

    def test_http_url(self):
        r = Response("http://example.com/path/to/resource")
        assert r.get_base_url() == "http://example.com"

    def test_url_with_port(self):
        r = Response("https://example.com:8080/api/data")
        assert r.get_base_url() == "https://example.com:8080"

    def test_url_with_query_params(self):
        r = Response("https://example.com/api?key=value")
        assert r.get_base_url() == "https://example.com"


class TestMethodValidation:
    def test_get_method(self):
        r = Response("https://example.com", method="GET")
        assert r._method == "GET"

    def test_post_method(self):
        r = Response("https://example.com", method="POST")
        assert r._method == "POST"

    def test_unsupported_method_raises(self):
        r = Response("https://example.com", method="DELETE")
        with pytest.raises(MethodError, match="Unsupported method"):
            _ = r._method


class TestResponse:
    @patch("london_data_store.utils.response.requests")
    def test_get_json_from_response(self, mock_requests):
        data = {"key": "value"}
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = json.dumps(data).encode()
        mock_requests.get.return_value = mock_resp

        r = Response("https://example.com/api")
        result = r.get_json_from_response()
        assert result == data

    @patch("london_data_store.utils.response.requests")
    def test_get_json_returns_none_on_error(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.raise_for_status.side_effect = Exception("Server error")
        mock_requests.get.return_value = mock_resp

        r = Response("https://example.com/api")
        result = r.get_json_from_response()
        assert result is None

    @patch("london_data_store.utils.response.requests")
    def test_response_caching(self, mock_requests):
        """Response should be cached after first access."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_requests.get.return_value = mock_resp

        r = Response("https://example.com/api")
        _ = r.response
        _ = r.response
        mock_requests.get.assert_called_once()

    @patch("london_data_store.utils.response.requests")
    def test_custom_headers_merged(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_requests.get.return_value = mock_resp

        r = Response("https://example.com", headers={"X-Custom": "test"})
        _ = r.response
        call_kwargs = mock_requests.get.call_args
        assert "X-Custom" in call_kwargs.kwargs.get("headers", call_kwargs[1].get("headers", {}))

    def test_timeout_attribute_exists(self):
        r = Response("https://example.com")
        assert r._timeout == 5

    @patch("london_data_store.utils.response.requests")
    def test_session_used_when_provided(self, mock_requests):
        """When a session is provided, it should be used instead of requests module."""
        mock_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_session.get.return_value = mock_resp

        r = Response("https://example.com", session=mock_session)
        _ = r.response
        mock_session.get.assert_called_once()
        mock_requests.get.assert_not_called()

    @patch("london_data_store.utils.response.requests")
    def test_no_session_uses_requests_module(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_requests.get.return_value = mock_resp

        r = Response("https://example.com")
        _ = r.response
        mock_requests.get.assert_called_once()


class TestSubclasses:
    def test_get_response_sets_method(self):
        r = GET_RESPONSE("https://example.com")
        assert r.method == "GET"

    def test_post_response_sets_method(self):
        r = POST_RESPONSE("https://example.com")
        assert r.method == "POST"
