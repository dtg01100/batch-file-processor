"""HTTP client implementations for send backends.

This module provides real and mock HTTP client implementations
that conform to the HTTPClientProtocol interface.
"""

import time
from typing import Any

import requests

from backend.protocols import HTTPClientProtocol
from core.structured_logging import (
    get_logger,
    get_or_create_correlation_id,
    log_backend_call,
)

logger = get_logger(__name__)


class RealHTTPClient:
    """Real HTTP client using requests library.

    This implementation wraps requests.post() for actual
    HTTP connections.

    Attributes:
        timeout: Default timeout for requests in seconds
        _session: The underlying requests session object

    """

    def __init__(self, timeout: float = 30.0) -> None:
        """Initialize HTTP client.

        Args:
            timeout: Default timeout for HTTP requests in seconds

        """
        self.timeout = timeout
        self._session: requests.Session | None = None

    def post(
        self,
        url: str,
        data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> requests.Response:
        """Send a POST request.

        Args:
            url: The URL to POST to
            data: Dictionary of form data (for non-file fields)
            files: Dictionary of files to upload (multipart/form-data)
            headers: Additional headers to include
            timeout: Request-specific timeout (overrides default)

        Returns:
            Response object

        Raises:
            requests.RequestException: If the request fails

        """
        get_or_create_correlation_id()
        start_time = time.perf_counter()
        effective_timeout = timeout if timeout is not None else self.timeout

        logger.debug("HTTP POST to %s", url)
        log_backend_call(logger, "http", "post", endpoint=url, success=None)

        try:
            if self._session is None:
                self._session = requests.Session()

            response = self._session.post(
                url,
                data=data,
                files=files,
                headers=headers,
                timeout=effective_timeout,
            )
            duration_ms = (time.perf_counter() - start_time) * 1000
            log_backend_call(
                logger,
                "http",
                "post",
                endpoint=url,
                success=True,
                duration_ms=duration_ms,
            )
            logger.debug(
                "HTTP POST to %s completed with status %s",
                url,
                response.status_code,
            )
            return response
        except requests.Timeout as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            log_backend_call(
                logger,
                "http",
                "post",
                endpoint=url,
                success=False,
                error=e,
                duration_ms=duration_ms,
            )
            logger.error("HTTP POST to %s timed out", url)
            raise
        except requests.RequestException as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            log_backend_call(
                logger,
                "http",
                "post",
                endpoint=url,
                success=False,
                error=e,
                duration_ms=duration_ms,
            )
            logger.error("HTTP POST to %s failed: %s", url, e)
            raise

    def close(self) -> None:
        """Close the HTTP session."""
        if self._session is not None:
            logger.debug("HTTP closing session")
            try:
                self._session.close()
            except Exception as e:
                logger.debug("Failed to close HTTP session: %s", e)
            finally:
                self._session = None


class MockHTTPClient:
    """Mock HTTP client for testing.

    This implementation records all operations for verification
    in tests without making actual HTTP connections.

    Attributes:
        posts: List of (url, data, files, headers) tuples from post calls
        errors: List of errors to raise on subsequent operations

    """

    def __init__(self) -> None:
        """Initialize mock HTTP client with empty tracking lists."""
        self.posts: list[tuple] = []
        self.errors: list[Exception] = []
        self._current_error_index = 0
        self._response_status_code: int = 200
        self._response_text: str = ""
        self._response_headers: dict[str, str] = {}

    def _raise_error_if_set(self) -> None:
        """Raise next error from errors list if available."""
        if self._current_error_index < len(self.errors):
            error = self.errors[self._current_error_index]
            self._current_error_index += 1
            raise error

    def post(
        self,
        url: str,
        data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> "MockHTTPResponse":
        """Record POST request.

        Args:
            url: The URL to POST to
            data: Dictionary of form data
            files: Dictionary of files to upload
            headers: Additional headers
            timeout: Request timeout (ignored in mock)

        Returns:
            MockHTTPResponse object

        """
        self._raise_error_if_set()
        self.posts.append((url, data, files, headers))
        return MockHTTPResponse(
            status_code=self._response_status_code,
            text=self._response_text,
            headers=self._response_headers,
        )

    def set_response(
        self,
        status_code: int = 200,
        text: str = "",
        headers: dict[str, str] | None = None,
    ) -> None:
        """Configure the response for the next POST.

        Args:
            status_code: HTTP status code to return
            text: Response body text
            headers: Response headers

        """
        self._response_status_code = status_code
        self._response_text = text
        self._response_headers = headers or {}

    def add_error(self, error: Exception) -> None:
        """Add an error to be raised on next POST.

        Args:
            error: Exception to raise

        """
        self.errors.append(error)

    def reset(self) -> None:
        """Reset all tracking state."""
        self.posts.clear()
        self.errors.clear()
        self._current_error_index = 0
        self._response_status_code = 200
        self._response_text = ""
        self._response_headers = {}


class MockHTTPResponse:
    """Mock HTTP response for testing.

    Attributes:
        status_code: HTTP status code
        text: Response body text
        headers: Response headers dictionary

    """

    def __init__(
        self,
        status_code: int,
        text: str = "",
        headers: dict[str, str] | None = None,
    ) -> None:
        """Initialize mock response.

        Args:
            status_code: HTTP status code
            text: Response body text
            headers: Response headers

        """
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}
        self.ok = 200 <= status_code < 300

    def json(self) -> Any:
        """Parse response body as JSON.

        Returns:
            Parsed JSON content

        Raises:
            ValueError: If text is not valid JSON

        """
        import json

        return json.loads(self.text)


def create_http_client(
    *, timeout: float = 30.0, mock: bool = False
) -> HTTPClientProtocol:
    """Factory function to create HTTP client.

    Args:
        timeout: Default timeout for requests in seconds
        mock: If True, return MockHTTPClient

    Returns:
        HTTP client instance

    """
    if mock:
        return MockHTTPClient()
    return RealHTTPClient(timeout=timeout)
