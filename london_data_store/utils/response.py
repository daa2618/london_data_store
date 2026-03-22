import json
import time
from urllib.parse import urlsplit

import requests

from .logging_helper import BasicLogger

_bl = BasicLogger(verbose=False, log_directory=None, logger_name="RESPONSE")


class MethodError(Exception):
    pass


class Response:
    _METHODS = ["GET", "POST"]

    def __init__(self, url: str, method: str = "GET", session: object = None, **kwargs):
        self.url = url
        self.kwargs = kwargs
        self.method = method
        self._session = session
        self._response = None
        self._user_agent = (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.517 Safari/537.36"
        )
        self._default_header = {"User-Agent": self._user_agent}
        self._timeout = 5

    @property
    def _method(self):
        if self.method not in self._METHODS:
            raise MethodError("Unsupported method")
        return self.method

    @property
    def response(self):

        params, headers = self.kwargs.get("params"), self._default_header
        if self._response is None:
            for x in ["headers", "header"]:
                val = self.kwargs.get(x)
                if val:
                    if isinstance(val, dict):
                        headers.update(val)
                    else:
                        _bl.warning("headers should be a dictionary")

            _kwargs = {key: value for key, value in self.kwargs.items() if key not in ["headers", "params"]}

            http_client = self._session if self._session else requests
            if self._method == "GET":
                self._response = http_client.get(self.url, params=params, headers=headers, **_kwargs)
            elif self._method == "POST":
                self._response = http_client.post(self.url, params=params, headers=headers, **_kwargs)
        return self._response

    def assert_response(self, await_response: bool = False):
        """Asserts that the HTTP response has a status code of 200 (OK).

        Waits for a response if `await_response` is True, polling until a response is received
        or a timeout occurs.  If a response is not received within the timeout period,
        an exception will not be explicitly raised; the function will continue.

        Args:
            await_response (bool, optional): If True, the function will wait for a response
                                            before asserting the status code. Defaults to False.

        Returns:
            requests.Response: The HTTP response object.

        Raises:
            requests.exceptions.HTTPError: If the response status code is not 200.
        """
        if self._response is None:
            if await_response:
                while self._response is None:
                    try:
                        self._response = self.response
                    except requests.RequestException:
                        _bl.warning("Request failed, retrying...")
                        time.sleep(self._timeout)
                        _bl.info("Retrying request...")
                        continue
            else:
                self._response = self.response

            assert self._response.status_code == 200, self._response.raise_for_status()
        return self._response

    def get_json_from_response(self, await_response: bool = False):
        """Extracts JSON data from a response object.

        This function attempts to parse the content of a response object as JSON.
        It first calls `self.assert_response(await_response)` to obtain the response.
        If the parsing is successful, it returns the resulting JSON object.
        If an error occurs during JSON parsing, it logs the error and returns None.

        Args:
            await_response: A boolean indicating whether to wait for the response. Defaults to False.

        Returns:
            A Python dictionary or list representing the parsed JSON data, or None if an error occurs.
        """
        try:
            return json.loads(self.assert_response(await_response).content)
        except Exception as e:
            # print(f"Error: \n\t {e}")
            _bl.error("Failed to get JSON from response", e)
            return None

    def get_base_url(self):
        """Extracts the base URL from a full URL.

        This function takes the full URL stored in the `self.url` attribute
        and returns only the base URL, consisting of the scheme (e.g., "https")
        and the network location (e.g., "www.example.com").  It uses the `urlsplit`
        function to parse the URL.

        Returns:
            str: The base URL (scheme://netloc).
        """
        split_url = urlsplit(self.url)
        return "://".join([split_url.scheme, split_url.netloc])


class GET_RESPONSE(Response):
    def __init__(self, url: str, **kwargs):
        super().__init__(method="GET", url=url, **kwargs)


class POST_RESPONSE(Response):
    def __init__(self, url: str, **kwargs):
        super().__init__(method="POST", url=url, **kwargs)
