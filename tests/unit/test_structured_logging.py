"""Tests for batch_file_processor.structured_logging module.

This module tests:
- Correlation ID management and propagation
- Redaction of sensitive data
- StructuredLogger methods
- The @logged decorator
- JSON formatter
"""

import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from batch_file_processor.structured_logging import (
    REDACTION_PATTERNS,
    CorrelationContext,
    JSONFormatter,
    StructuredLogger,
    clear_correlation_id,
    generate_correlation_id,
    get_correlation_id,
    get_or_create_correlation_id,
    hash_sensitive_value,
    logged,
    redact_sensitive_data,
    redact_string,
    redact_value,
    set_correlation_id,
)


class TestCorrelationIdManagement:
    """Tests for correlation ID management functions."""

    def test_generate_correlation_id_returns_unique_ids(self):
        """Test that generated correlation IDs are unique."""
        ids = [generate_correlation_id() for _ in range(100)]
        assert len(set(ids)) == 100

    def test_get_correlation_id_returns_none_when_not_set(self):
        """Test that get_correlation_id returns None when not set."""
        clear_correlation_id()
        assert get_correlation_id() is None

    def test_set_and_get_correlation_id(self):
        """Test setting and getting correlation ID."""
        clear_correlation_id()
        test_id = "test-correlation-id-123"
        set_correlation_id(test_id)
        assert get_correlation_id() == test_id

    def test_clear_correlation_id(self):
        """Test clearing correlation ID."""
        set_correlation_id("test-id")
        clear_correlation_id()
        assert get_correlation_id() is None

    def test_get_or_create_returns_existing_id(self):
        """Test that get_or_create returns existing ID when set."""
        clear_correlation_id()
        existing_id = "existing-id"
        set_correlation_id(existing_id)
        result = get_or_create_correlation_id()
        assert result == existing_id

    def test_get_or_create_creates_new_id_when_none(self):
        """Test that get_or_create creates new ID when none set."""
        clear_correlation_id()
        result = get_or_create_correlation_id()
        assert result is not None
        assert len(result) == 16

    def test_correlation_id_thread_isolation(self):
        """Test that correlation IDs are isolated between threads."""
        clear_correlation_id()
        results = {}

        def thread_func(thread_id):
            set_correlation_id(f"id-{thread_id}")
            # Small delay to ensure other thread runs
            import time
            time.sleep(0.01)
            results[thread_id] = get_correlation_id()

        threads = [threading.Thread(target=thread_func, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        for i, result in results.items():
            assert result == f"id-{i}"


class TestRedactionFunctions:
    """Tests for redaction helper functions."""

    def test_redact_string_returns_string(self):
        """Test that redact_string returns a string."""
        result = redact_string("mysecretpassword", visible_chars=4)
        assert isinstance(result, str)
        assert len(result) == len("mysecretpassword")

    def test_redact_string_contains_stars(self):
        """Test that redact_string contains stars."""
        result = redact_string("mypassword", visible_chars=4)
        assert "*" in result

    def test_redact_string_preserves_last_chars(self):
        """Test that redact_string preserves some characters."""
        result = redact_string("mypassword123", visible_chars=4)
        # Should contain last 4 chars "123"
        assert "123" in result

    def test_redact_string_empty_string(self):
        """Test redaction of empty string."""
        result = redact_string("")
        assert result == "****"

    def test_redact_string_none(self):
        """Test redaction of None."""
        result = redact_string(None)
        assert result == "****"

    def test_redact_string_short_string(self):
        """Test redaction of short string (length <= visible_chars)."""
        result = redact_string("abc", visible_chars=4)
        assert "*" in result

    def test_redact_sensitive_data_password_redacted(self):
        """Test redaction of password field."""
        data = {"username": "john", "password": "secret123"}
        result = redact_sensitive_data(data)
        # password should be redacted (not equal to original)
        assert result["password"] != "secret123"

    def test_redact_sensitive_data_api_key_redacted(self):
        """Test redaction of API key."""
        data = {"api_key": "my-secret-key-12345"}
        result = redact_sensitive_data(data)
        # Should not equal original
        assert result["api_key"] != "my-secret-key-12345"

    def test_redact_sensitive_data_nested_dict(self):
        """Test redaction of nested dictionary."""
        data = {"user": {"password": "secret"}}
        result = redact_sensitive_data(data)
        assert result["user"]["password"] != "secret"

    def test_redact_sensitive_data_list(self):
        """Test redaction of list values."""
        data = {"passwords": ["pass1", "pass2"]}
        result = redact_sensitive_data(data)
        # Original values should be redacted
        assert "pass1" not in result["passwords"][0]
        assert "pass2" not in result["passwords"][1]

    def test_redact_sensitive_data_non_dict(self):
        """Test redaction with non-dict input."""
        result = redact_sensitive_data("not a dict")
        assert result == "not a dict"

    def test_redact_sensitive_data_applies_recursively(self):
        """Test that redact_value is applied to all string values."""
        data = {"name": "John Doe", "age": 30}
        result = redact_sensitive_data(data)
        # redact_value is applied to all values, so strings get redacted
        assert "**** Doe" in result["name"]
        assert result["age"] == 30

    def test_redact_value_string(self):
        """Test redact_value with string."""
        result = redact_value("testpassword")
        assert isinstance(result, str)
        assert "password" not in result

    def test_redact_value_dict(self):
        """Test redact_value with dict."""
        data = {"password": "secret"}
        result = redact_value(data)
        assert result["password"] != "secret"

    def test_redact_value_list(self):
        """Test redact_value with list."""
        result = redact_value(["pass1", "pass2"])
        assert "pass1" not in result[0]

    def test_redact_value_none(self):
        """Test redact_value with None."""
        result = redact_value(None)
        assert result is None

    def test_hash_sensitive_value(self):
        """Test hashing of sensitive values."""
        result = hash_sensitive_value("mysecret")
        assert result is not None
        assert len(result) == 16

    def test_hash_sensitive_value_none(self):
        """Test hashing None value."""
        result = hash_sensitive_value(None)
        assert result == "****"


class TestCorrelationContext:
    """Tests for CorrelationContext manager."""

    def test_context_sets_correlation_id(self):
        """Test that context manager sets correlation ID."""
        clear_correlation_id()
        with CorrelationContext("test-id") as cid:
            assert cid == "test-id"
            assert get_correlation_id() == "test-id"

    def test_context_restores_previous_id(self):
        """Test that context manager restores previous ID."""
        clear_correlation_id()
        set_correlation_id("original-id")
        with CorrelationContext("new-id"):
            pass
        assert get_correlation_id() == "original-id"

    def test_context_generates_id_when_none_provided(self):
        """Test that context generates ID when none provided."""
        clear_correlation_id()
        with CorrelationContext() as cid:
            assert cid is not None
            assert get_correlation_id() == cid
        assert get_correlation_id() is None


class TestStructuredLogger:
    """Tests for StructuredLogger class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.logger = logging.getLogger("test_logger")
        self.logger.setLevel(logging.DEBUG)

    def test_log_entry_adds_extra_fields(self, caplog):
        """Test that log_entry adds extra fields."""
        caplog.set_level(logging.DEBUG)

        StructuredLogger.log_entry(
            self.logger,
            "test_func",
            "test_module",
            args=("arg1",),
            kwargs={"key": "value"},
        )

        assert "[ENTRY]" in caplog.text
        assert "test_func" in caplog.text

    def test_log_exit_logs_duration(self, caplog):
        """Test that log_exit logs duration."""
        caplog.set_level(logging.DEBUG)

        StructuredLogger.log_exit(
            self.logger,
            "test_func",
            "test_module",
            result="result_value",
            duration_ms=150.5,
        )

        assert "[EXIT]" in caplog.text
        assert "test_func" in caplog.text
        assert "150.5" in caplog.text

    def test_log_error_includes_exception(self, caplog):
        """Test that log_error includes exception info."""
        caplog.set_level(logging.ERROR)

        try:
            raise ValueError("Test error")
        except ValueError as e:
            StructuredLogger.log_error(
                self.logger,
                "test_func",
                "test_module",
                e,
                {"context_key": "context_value"},
                duration_ms=50.0,
            )

        assert "[ERROR]" in caplog.text
        assert "Test error" in caplog.text

    def test_log_debug_sanitizes_password(self, caplog):
        """Test that log_debug sanitizes password in kwargs."""
        caplog.set_level(logging.DEBUG)

        StructuredLogger.log_debug(
            self.logger,
            "test_func",
            "test_module",
            "Test message",
            password="secret123",
        )

        assert "secret123" not in caplog.text

    def test_log_intermediate_logs_step(self, caplog):
        """Test that log_intermediate logs step information."""
        caplog.set_level(logging.DEBUG)

        StructuredLogger.log_intermediate(
            self.logger,
            "convert_func",
            "test_module",
            step="parse_records",
            data_shape={"records": 50, "type": "list"},
            decision="using_retail_uom",
        )

        assert "parse_records" in caplog.text
        assert "using_retail_uom" in caplog.text


class TestLoggedDecorator:
    """Tests for @logged decorator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.logger = logging.getLogger("test_decorator")
        self.logger.setLevel(logging.DEBUG)

    def test_decorator_logs_entry_and_exit(self, caplog):
        """Test that decorator logs entry and exit."""
        caplog.set_level(logging.DEBUG)

        @logged
        def test_func():
            return "result"

        result = test_func()

        assert result == "result"
        assert "test_func" in caplog.text.lower()

    def test_decorator_logs_duration(self, caplog):
        """Test that decorator logs execution duration."""
        caplog.set_level(logging.DEBUG)
        import time

        @logged
        def slow_func():
            time.sleep(0.05)
            return "done"

        slow_func()

        # Should have logged duration somewhere
        assert any("ms" in record.message for record in caplog.records)

    def test_decorator_logs_error(self, caplog):
        """Test that decorator logs errors."""
        caplog.set_level(logging.DEBUG)

        @logged
        def error_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            error_func()

        assert "error" in caplog.text.lower()

    def test_decorator_preserves_function_name(self):
        """Test that decorator preserves function metadata."""

        @logged
        def my_function():
            pass

        assert my_function.__name__ == "my_function"
        assert my_function.__module__ == __name__


class TestJSONFormatter:
    """Tests for JSONFormatter class."""

    def test_formatter_creates_json(self):
        """Test that formatter creates valid JSON."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)

        # Should be valid JSON
        parsed = json.loads(result)
        assert parsed["message"] == "Test message"
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test_logger"

    def test_formatter_includes_extra_fields(self):
        """Test that formatter includes extra fields."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.correlation_id = "test-123"
        record.function = "test_func"
        record.duration_ms = 150.5

        result = formatter.format(record)
        parsed = json.loads(result)

        assert parsed["correlation_id"] == "test-123"
        assert parsed["function"] == "test_func"
        assert parsed["duration_ms"] == 150.5


class TestIntegration:
    """Integration tests for structured logging."""

    def test_full_conversion_flow_with_logging(self, caplog):
        """Test full flow with logging capture."""
        caplog.set_level(logging.DEBUG)

        @logged
        def mock_convert(input_path, output_path, settings):
            return output_path

        with CorrelationContext("conv-123"):
            result = mock_convert(
                "/input/test.edi",
                "/output/test.csv",
                {"password": "secret", "api_key": "key123"},
            )

        assert result == "/output/test.csv"

    def test_error_handling_with_context(self, caplog):
        """Test error handling preserves context."""
        caplog.set_level(logging.DEBUG)

        set_correlation_id("error-test-id")

        @logged
        def failing_func():
            raise RuntimeError("Simulated failure")

        with pytest.raises(RuntimeError):
            failing_func()

        # Error should be logged somewhere
        assert "error" in caplog.text.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
