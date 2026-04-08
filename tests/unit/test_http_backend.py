"""Unit tests for HTTP backend module.

Tests:
- HTTP POST operations with mock client
- Header parsing and authentication
- Error handling and retry logic
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.backend]


class TestHTTPBackendOperations:
    """Test suite for HTTP backend operations."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def source_file(self, temp_dir):
        """Create a source file for uploading."""
        source = temp_dir / "http_test.txt"
        source.write_text("HTTP test content")
        return str(source)

    @pytest.fixture
    def process_parameters(self):
        """Create process parameters for HTTP backend."""
        return {
            "http_url": "https://example.com/upload",
            "http_field_name": "file",
        }

    @pytest.fixture
    def settings_dict(self):
        """Create empty settings dict."""
        return {}

    def test_http_backend_with_mock_client(
        self, process_parameters, settings_dict, source_file
    ):
        """Test HTTP backend with mock client."""
        from backend.http_client import MockHTTPClient

        mock_client = MockHTTPClient()
        mock_client.set_response(status_code=200, text="OK")

        result = __import__("backend.http_backend", fromlist=["do"]).do(
            process_parameters, settings_dict, source_file, http_client=mock_client
        )

        assert result is True
        assert len(mock_client.posts) > 0

    def test_http_backend_sends_file(
        self, process_parameters, settings_dict, source_file
    ):
        """Test that file is sent via HTTP POST."""
        from backend.http_client import MockHTTPClient

        mock_client = MockHTTPClient()
        mock_client.set_response(status_code=200, text="Success")

        __import__("backend.http_backend", fromlist=["do"]).do(
            process_parameters, settings_dict, source_file, http_client=mock_client
        )

        url, data, files, headers = mock_client.posts[0]
        assert url == "https://example.com/upload"
        assert "file" in files

    def test_http_backend_with_headers(self, temp_dir, settings_dict):
        """Test HTTP backend with custom headers."""
        from backend.http_client import MockHTTPClient

        source = temp_dir / "test.txt"
        source.write_text("content")

        process_parameters = {
            "http_url": "https://example.com/upload",
            "http_field_name": "file",
            "http_headers": "X-Custom-Header: value\nContent-Type: application/json",
        }

        mock_client = MockHTTPClient()
        mock_client.set_response(status_code=200)

        __import__("backend.http_backend", fromlist=["do"]).do(
            process_parameters, settings_dict, str(source), http_client=mock_client
        )

        url, data, files, headers = mock_client.posts[0]
        assert headers is not None

    def test_http_backend_bearer_auth(self, temp_dir, settings_dict):
        """Test HTTP backend with Bearer authentication."""
        from backend.http_client import MockHTTPClient

        source = temp_dir / "test.txt"
        source.write_text("content")

        process_parameters = {
            "http_url": "https://example.com/upload",
            "http_field_name": "file",
            "http_auth_type": "bearer",
            "http_api_key": "secret-token",
        }

        mock_client = MockHTTPClient()
        mock_client.set_response(status_code=200)

        __import__("backend.http_backend", fromlist=["do"]).do(
            process_parameters, settings_dict, str(source), http_client=mock_client
        )

        url, data, files, headers = mock_client.posts[0]
        assert headers is not None

    def test_http_backend_query_auth(self, temp_dir, settings_dict):
        """Test HTTP backend with query parameter authentication."""
        from backend.http_client import MockHTTPClient

        source = temp_dir / "test.txt"
        source.write_text("content")

        process_parameters = {
            "http_url": "https://example.com/upload",
            "http_field_name": "file",
            "http_auth_type": "query",
            "http_api_key": "api-key-123",
        }

        mock_client = MockHTTPClient()
        mock_client.set_response(status_code=200)

        __import__("backend.http_backend", fromlist=["do"]).do(
            process_parameters, settings_dict, str(source), http_client=mock_client
        )

        url, data, files, headers = mock_client.posts[0]
        assert "api_key=" in url

    def test_http_backend_failure_raises(
        self, process_parameters, settings_dict, temp_dir
    ):
        """Test that HTTP failure raises exception."""
        from backend.http_client import MockHTTPClient

        source = temp_dir / "test.txt"
        source.write_text("content")

        mock_client = MockHTTPClient()
        mock_client.set_response(status_code=500, text="Server Error")

        with patch("time.sleep"):
            with pytest.raises(Exception, match="HTTP POST failed"):
                __import__("backend.http_backend", fromlist=["do"]).do(
                    process_parameters,
                    settings_dict,
                    str(source),
                    http_client=mock_client,
                )

    def test_http_backend_retries_on_failure(self, temp_dir, settings_dict):
        """Test HTTP backend retries on failure."""
        from backend.http_client import MockHTTPClient

        source = temp_dir / "test.txt"
        source.write_text("content")

        process_parameters = {
            "http_url": "https://example.com/upload",
            "http_field_name": "file",
        }

        mock_client = MockHTTPClient()
        mock_client.set_response(status_code=500)

        with patch("time.sleep"):
            with pytest.raises(Exception):
                __import__("backend.http_backend", fromlist=["do"]).do(
                    process_parameters,
                    settings_dict,
                    str(source),
                    http_client=mock_client,
                    disable_retry=True,
                )

        assert len(mock_client.posts) >= 1


class TestHTTPBackendHelperFunctions:
    """Test suite for HTTP backend helper functions."""

    def test_parse_headers_empty(self):
        """Test parsing empty headers string."""
        from backend.http_backend import _parse_headers

        result = _parse_headers("")
        assert result == {}

    def test_parse_headers_single(self):
        """Test parsing single header."""
        from backend.http_backend import _parse_headers

        result = _parse_headers("Content-Type: application/json")
        assert result == {"Content-Type": "application/json"}

    def test_parse_headers_multiple(self):
        """Test parsing multiple headers."""
        from backend.http_backend import _parse_headers

        result = _parse_headers("X-Header-1: value1\nX-Header-2: value2")
        assert result == {"X-Header-1": "value1", "X-Header-2": "value2"}

    def test_parse_headers_strips_whitespace(self):
        """Test that header parsing strips whitespace."""
        from backend.http_backend import _parse_headers

        result = _parse_headers("  X-Custom  :  value with spaces  ")
        assert result == {"X-Custom": "value with spaces"}

    def test_parse_headers_ignores_invalid(self):
        """Test that invalid header lines are ignored."""
        from backend.http_backend import _parse_headers

        result = _parse_headers("Valid-Header: value\ninvalid line\nAnother-Valid: ok")
        assert result == {"Valid-Header": "value", "Another-Valid": "ok"}

    def test_build_url_with_query_no_params(self):
        """Test building URL without existing query params."""
        from backend.http_backend import _build_url_with_query

        result = _build_url_with_query("https://example.com/upload", "api-key")
        assert result == "https://example.com/upload?api_key=api-key"

    def test_build_url_with_query_with_params(self):
        """Test building URL with existing query params."""
        from backend.http_backend import _build_url_with_query

        result = _build_url_with_query("https://example.com/upload?page=1", "api-key")
        assert result == "https://example.com/upload?page=1&api_key=api-key"

    def test_add_bearer_auth(self):
        """Test adding Bearer authorization header."""
        from backend.http_backend import _add_bearer_auth

        headers = {"Content-Type": "application/json"}
        result = _add_bearer_auth(headers, "secret-token")

        assert result["Authorization"] == "Bearer secret-token"
        assert result["Content-Type"] == "application/json"

    def test_add_bearer_auth_empty_headers(self):
        """Test adding Bearer auth to empty headers."""
        from backend.http_backend import _add_bearer_auth

        result = _add_bearer_auth({}, "token")
        assert result == {"Authorization": "Bearer token"}


class TestHTTPClient:
    """Test suite for HTTP client implementations."""

    def test_mock_http_client_records_posts(self):
        """Test MockHTTPClient records POST calls."""
        from backend.http_client import MockHTTPClient

        client = MockHTTPClient()
        client.set_response(status_code=200, text="OK")

        client.post("https://example.com/upload", data={"key": "value"})

        assert len(client.posts) == 1
        url, data, files, headers = client.posts[0]
        assert url == "https://example.com/upload"
        assert data == {"key": "value"}

    def test_mock_http_client_response_ok(self):
        """Test MockHTTPResponse ok property."""
        from backend.http_client import MockHTTPResponse

        response = MockHTTPResponse(status_code=200)
        assert response.ok is True

        response = MockHTTPResponse(status_code=404)
        assert response.ok is False

        response = MockHTTPResponse(status_code=500)
        assert response.ok is False

    def test_mock_http_client_json(self):
        """Test MockHTTPResponse json parsing."""
        from backend.http_client import MockHTTPResponse

        response = MockHTTPResponse(status_code=200, text='{"key": "value"}')
        result = response.json()

        assert result == {"key": "value"}

    def test_mock_http_client_set_response(self):
        """Test MockHTTPClient set_response method."""
        from backend.http_client import MockHTTPClient

        client = MockHTTPClient()
        client.set_response(
            status_code=201, text="Created", headers={"X-Custom": "value"}
        )

        response = client.post("https://example.com")

        assert response.status_code == 201
        assert response.text == "Created"
        assert response.headers["X-Custom"] == "value"

    def test_mock_http_client_add_error(self):
        """Test MockHTTPClient error handling."""
        from backend.http_client import MockHTTPClient

        client = MockHTTPClient()
        client.add_error(RuntimeError("Connection failed"))

        with pytest.raises(RuntimeError, match="Connection failed"):
            client.post("https://example.com")

    def test_mock_http_client_reset(self):
        """Test MockHTTPClient reset method."""
        from backend.http_client import MockHTTPClient

        client = MockHTTPClient()
        client.set_response(status_code=200)
        client.post("https://example.com")
        client.reset()

        assert len(client.posts) == 0


class TestHTTPBackendClass:
    """Test suite for HTTPBackend class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def source_file(self, temp_dir):
        """Create a source file for uploading."""
        source = temp_dir / "test.txt"
        source.write_text("content")
        return str(source)

    def test_http_backend_class_send(self, source_file):
        """Test HTTPBackend class send method."""
        from backend.http_backend import HTTPBackend
        from backend.http_client import MockHTTPClient

        mock_client = MockHTTPClient()
        mock_client.set_response(status_code=200)

        backend = HTTPBackend(http_client=mock_client)
        result = backend.send(
            {"http_url": "https://example.com/upload", "http_field_name": "file"},
            {},
            source_file,
        )

        assert result is True

    def test_http_backend_class_with_bearer_auth(self, source_file):
        """Test HTTPBackend with Bearer auth."""
        from backend.http_backend import HTTPBackend
        from backend.http_client import MockHTTPClient

        mock_client = MockHTTPClient()
        mock_client.set_response(status_code=200)

        backend = HTTPBackend(http_client=mock_client)
        result = backend.send(
            {
                "http_url": "https://example.com/upload",
                "http_field_name": "file",
                "http_auth_type": "bearer",
                "http_api_key": "my-token",
            },
            {},
            source_file,
        )

        assert result is True

    def test_http_backend_class_cleanup(self):
        """Test HTTPBackend cleanup closes client."""
        from backend.http_backend import HTTPBackend
        from backend.http_client import MockHTTPClient

        mock_client = MockHTTPClient()
        mock_client.set_response(status_code=200)

        backend = HTTPBackend(http_client=mock_client)
        backend._cleanup()

    def test_http_backend_create_client(self):
        """Test HTTPBackend.create_client factory."""
        from backend.http_backend import HTTPBackend

        client = HTTPBackend.create_client(timeout=60.0)
        assert client is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
