"""HTTP backend for sending files via HTTP POST.

This module sends files via HTTP POST with multipart/form-data
with injectable client support for testing.
"""

import os
import time

from backend.http_client import create_http_client
from backend.protocols import HTTPClientProtocol
from core.structured_logging import (
    get_logger,
    log_backend_call,
    log_file_operation,
)

logger = get_logger(__name__)


def _parse_headers(headers_string: str) -> dict[str, str]:
    """Parse newline-separated headers into a dictionary.

    Args:
        headers_string: Newline-separated "Key: Value" pairs

    Returns:
        Dictionary of header name to value mappings

    """
    if not headers_string:
        return {}
    return {
        key.strip(): value.strip()
        for raw in headers_string.strip().split("\n")
        if (line := raw.strip()) and ":" in line
        for key, value in [line.split(":", 1)]
    }


def _build_url_with_query(url: str, api_key: str) -> str:
    """Append API key as query parameter to URL.

    Args:
        url: Base URL
        api_key: API key value

    Returns:
        URL with api_key query parameter appended

    """
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}api_key={api_key}"


def _add_bearer_auth(headers: dict[str, str], api_key: str) -> dict[str, str]:
    """Add Bearer token authorization header.

    Args:
        headers: Existing headers dictionary
        api_key: API key value

    Returns:
        Updated headers with Authorization header added

    """
    headers = dict(headers)
    headers["Authorization"] = f"Bearer {api_key}"
    return headers


def do(
    process_parameters: dict,
    settings_dict: dict,
    filename: str,
    http_client: HTTPClientProtocol | None = None,
) -> bool:
    """Send a file via HTTP POST.

    Args:
        process_parameters: Dictionary containing HTTP configuration:
            - http_url: Endpoint URL (required)
            - http_headers: Newline-separated custom headers (optional)
            - http_field_name: Form field name for file (default: "file")
            - http_auth_type: "bearer" or "query" (optional)
            - http_api_key: API key value (optional)
        settings_dict: Settings dictionary (not used by HTTP backend)
        filename: Local file path to send
        http_client: Optional injectable HTTP client for testing.
                    If None, creates real HTTP client.

    Returns:
        True if file was sent successfully

    Raises:
        Exception: If file cannot be sent after 10 retries

    """
    file_pass = False
    counter = 0
    correlation_id = os.urandom(4).hex()

    log_file_operation(
        logger,
        "read",
        filename,
        file_type="edi",
        correlation_id=correlation_id,
    )

    while not file_pass:
        try:
            if http_client is not None:
                client = http_client
            else:
                client = create_http_client()

            try:
                url = process_parameters["http_url"]
                headers_string = process_parameters.get("http_headers", "")
                field_name = process_parameters.get("http_field_name", "file")
                auth_type = process_parameters.get("http_auth_type", "")
                api_key = process_parameters.get("http_api_key", "")

                parsed_headers = _parse_headers(headers_string)

                if auth_type == "bearer" and api_key:
                    parsed_headers = _add_bearer_auth(parsed_headers, api_key)
                    final_url = url
                elif auth_type == "query" and api_key:
                    final_url = _build_url_with_query(url, api_key)
                else:
                    final_url = url

                file_basename = os.path.basename(filename)
                file_size = os.path.getsize(filename)

                with open(filename, "rb") as f:
                    files = {field_name: (file_basename, f)}
                    data: dict = {}

                    start_time = time.perf_counter()
                    logger.debug("HTTP POSTing file %s to %s", file_basename, final_url)
                    log_backend_call(
                        logger,
                        "http",
                        "upload",
                        endpoint=final_url,
                        success=None,
                        correlation_id=correlation_id,
                    )

                    response = client.post(
                        final_url,
                        data=data,
                        files=files,
                        headers=parsed_headers,
                    )

                    duration_ms = (time.perf_counter() - start_time) * 1000

                    if response.ok:
                        log_backend_call(
                            logger,
                            "http",
                            "upload",
                            endpoint=final_url,
                            success=True,
                            duration_ms=duration_ms,
                            correlation_id=correlation_id,
                        )
                        log_file_operation(
                            logger,
                            "write",
                            file_basename,
                            file_size=file_size,
                            file_type="edi",
                            success=True,
                            correlation_id=correlation_id,
                        )
                        logger.info(
                            "Successfully sent file %s via HTTP to %s",
                            file_basename,
                            final_url,
                        )
                        file_pass = True
                    else:
                        error_msg = (
                            f"HTTP POST failed with status {response.status_code}: "
                            f"{response.text[:500]}"
                        )
                        log_backend_call(
                            logger,
                            "http",
                            "upload",
                            endpoint=final_url,
                            success=False,
                            error=error_msg,
                            duration_ms=duration_ms,
                            correlation_id=correlation_id,
                        )
                        log_file_operation(
                            logger,
                            "write",
                            file_basename,
                            file_size=file_size,
                            file_type="edi",
                            success=False,
                            correlation_id=correlation_id,
                        )
                        raise Exception(error_msg)

            finally:
                try:
                    client.close()
                except Exception as e:
                    logger.debug("Failed to close HTTP client: %s", e)

        except Exception as http_error:
            if counter == 10:
                logger.error("HTTP retry limit reached, passing exception to dispatch")
                log_backend_call(
                    logger,
                    "http",
                    "upload",
                    endpoint=process_parameters.get("http_url", ""),
                    success=False,
                    error=http_error,
                    retry_count=counter,
                    correlation_id=correlation_id,
                )
                raise
            counter += 1
            logger.warning(
                "HTTP send encountered an error. Retry number %d: %s",
                counter,
                http_error,
            )
            time.sleep(2)

    return file_pass


class HTTPBackend:
    """HTTP backend class for object-oriented usage.

    Provides an object-oriented interface to the HTTP backend
    with injectable client support.

    Attributes:
        http_client: HTTP client instance (injectable for testing)

    """

    def __init__(self, http_client: HTTPClientProtocol | None = None) -> None:
        """Initialize HTTP backend.

        Args:
            http_client: Optional injectable HTTP client for testing.

        """
        self.http_client = http_client

    def send(
        self, process_parameters: dict, settings_dict: dict, filename: str
    ) -> bool:
        """Send a file via HTTP POST.

        Args:
            process_parameters: HTTP connection parameters
            settings_dict: Settings dictionary
            filename: File to send

        Returns:
            True if successful

        """
        return do(process_parameters, settings_dict, filename, self.http_client)

    @staticmethod
    def create_client(timeout: float = 30.0) -> HTTPClientProtocol:
        """Create an HTTP client.

        Args:
            timeout: Request timeout in seconds

        Returns:
            HTTP client instance

        """
        return create_http_client(timeout=timeout)
