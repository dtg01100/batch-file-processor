"""
Comprehensive unit tests for send_base.py module.

Tests the BaseSendBackend abstract class and create_send_wrapper function.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

import pytest

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import send_base
from send_base import BaseSendBackend, create_send_wrapper


class MockSendBackend(BaseSendBackend):
    """Mock send backend for testing."""

    PLUGIN_ID = "mock"
    PLUGIN_NAME = "Mock Backend"
    PLUGIN_DESCRIPTION = "Test backend"
    CONFIG_FIELDS = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.send_called = False
        self.send_count = 0

    def _send(self):
        """Mock send implementation."""
        self.send_called = True
        self.send_count += 1


class FailingSendBackend(BaseSendBackend):
    """Backend that always fails for testing retry logic."""

    PLUGIN_ID = "failing"
    PLUGIN_NAME = "Failing Backend"
    PLUGIN_DESCRIPTION = "Always fails"
    CONFIG_FIELDS = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attempt_count = 0

    def _send(self):
        """Always raises exception."""
        self.attempt_count += 1
        raise Exception("Send failed")


class SuccessAfterRetriesBackend(BaseSendBackend):
    """Backend that succeeds after a few retries."""

    PLUGIN_ID = "eventual_success"
    PLUGIN_NAME = "Eventual Success Backend"
    PLUGIN_DESCRIPTION = "Succeeds after retries"
    CONFIG_FIELDS = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attempt_count = 0
        self.success_after = 3  # Succeed on 3rd attempt

    def _send(self):
        """Fail first 2 times, succeed on 3rd."""
        self.attempt_count += 1
        if self.attempt_count < self.success_after:
            raise Exception(f"Attempt {self.attempt_count} failed")


class ExponentialBackoffBackend(BaseSendBackend):
    """Backend with exponential backoff enabled."""

    PLUGIN_ID = "exponential"
    PLUGIN_NAME = "Exponential Backend"
    PLUGIN_DESCRIPTION = "Uses exponential backoff"
    CONFIG_FIELDS = []
    exponential_backoff = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attempt_count = 0

    def _send(self):
        """Always fail to test backoff."""
        self.attempt_count += 1
        if self.attempt_count <= 10:
            raise Exception("Failed")


class TestBaseSendBackend(unittest.TestCase):
    """Tests for BaseSendBackend class."""

    def test_init(self):
        """Test backend initialization."""
        process_params = {'param1': 'value1', 'param2': 'value2'}
        settings = {'setting1': 'value1'}
        filename = '/path/to/file.txt'

        backend = MockSendBackend(process_params, settings, filename)

        self.assertEqual(backend.process_parameters, process_params)
        self.assertEqual(backend.parameters_dict, process_params)
        self.assertEqual(backend.settings_dict, settings)
        self.assertEqual(backend.filename, filename)

    def test_send_success(self):
        """Test successful send."""
        backend = MockSendBackend({}, {}, 'file.txt')

        backend.send()

        self.assertTrue(backend.send_called)
        self.assertEqual(backend.send_count, 1)

    def test_send_success_after_retries(self):
        """Test send succeeds after retries."""
        backend = SuccessAfterRetriesBackend({}, {}, 'file.txt')

        backend.send()

        self.assertEqual(backend.attempt_count, 3)

    def test_send_retry_limit_exceeded(self):
        """Test send raises after max retries exceeded."""
        backend = FailingSendBackend({}, {}, 'file.txt')

        with self.assertRaises(Exception) as context:
            backend.send()

        self.assertIn("Send failed", str(context.exception))
        self.assertEqual(backend.attempt_count, 11)  # Initial + 10 retries

    @patch('send_base.time.sleep')
    def test_exponential_backoff(self, mock_sleep):
        """Test exponential backoff is applied."""
        backend = ExponentialBackoffBackend({}, {}, 'file.txt')

        with self.assertRaises(Exception):
            backend.send()

        # Should have called sleep with increasing delays (1, 4, 9, 16...)
        self.assertTrue(mock_sleep.called)
        # Check that sleep was called with increasing values
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        self.assertEqual(sleep_calls, [1, 4, 9, 16, 25, 36, 49, 64, 81, 100])

    @patch('send_base.time.sleep')
    def test_simple_retry_no_backoff(self, mock_sleep):
        """Test that backends without exponential_backoff don't sleep."""
        backend = FailingSendBackend({}, {}, 'file.txt')

        with self.assertRaises(Exception):
            backend.send()

        # Should not call sleep for non-exponential backoff
        mock_sleep.assert_not_called()


class TestCreateSendWrapper(unittest.TestCase):
    """Tests for create_send_wrapper function."""

    def test_wrapper_creates_callable(self):
        """Test wrapper creates a callable function."""
        wrapper = create_send_wrapper(MockSendBackend)

        self.assertTrue(callable(wrapper))

    def test_wrapper_executes_send(self):
        """Test wrapper executes the send operation."""
        wrapper = create_send_wrapper(MockSendBackend)

        process_params = {'param': 'value'}
        settings = {'setting': 'value'}
        filename = 'test.txt'

        # Should execute without error
        wrapper(process_params, settings, filename)

    def test_wrapper_passes_parameters(self):
        """Test wrapper passes parameters to backend."""
        # Create a backend that records its initialization
        class RecordingBackend(BaseSendBackend):
            PLUGIN_ID = "recording"
            PLUGIN_NAME = "Recording Backend"
            PLUGIN_DESCRIPTION = "Records init params"
            CONFIG_FIELDS = []

            init_calls = []

            def __init__(self, process_parameters, settings_dict, filename):
                super().__init__(process_parameters, settings_dict, filename)
                RecordingBackend.init_calls.append({
                    'process_parameters': process_parameters,
                    'settings_dict': settings_dict,
                    'filename': filename
                })

            def _send(self):
                pass

        RecordingBackend.init_calls = []
        wrapper = create_send_wrapper(RecordingBackend)

        process_params = {'test_param': 'test_value'}
        settings = {'test_setting': 'test_value'}
        filename = '/path/to/file.txt'

        wrapper(process_params, settings, filename)

        self.assertEqual(len(RecordingBackend.init_calls), 1)
        call = RecordingBackend.init_calls[0]
        self.assertEqual(call['process_parameters'], process_params)
        self.assertEqual(call['settings_dict'], settings)
        self.assertEqual(call['filename'], filename)

    def test_wrapper_function_name(self):
        """Test wrapper function is named 'do'."""
        wrapper = create_send_wrapper(MockSendBackend)

        self.assertEqual(wrapper.__name__, 'do')


class TestBaseSendBackendRetryLogic(unittest.TestCase):
    """Tests for retry logic in BaseSendBackend."""

    def test_retry_counter_increments(self):
        """Test that retry counter increments correctly."""
        backend = FailingSendBackend({}, {}, 'file.txt')

        with self.assertRaises(Exception):
            backend.send()

        # Should have attempted 11 times (initial + 10 retries)
        self.assertEqual(backend.attempt_count, 11)

    def test_no_retry_on_success(self):
        """Test that successful send doesn't retry."""
        backend = MockSendBackend({}, {}, 'file.txt')

        backend.send()

        # Should have succeeded on first attempt
        self.assertEqual(backend.send_count, 1)


class TestBaseSendBackendEdgeCases(unittest.TestCase):
    """Edge case tests for BaseSendBackend."""

    def test_empty_parameters(self):
        """Test backend with empty parameters."""
        backend = MockSendBackend({}, {}, '')

        backend.send()

        self.assertTrue(backend.send_called)

    def test_none_parameters(self):
        """Test backend with None parameters."""
        backend = MockSendBackend(None, None, None)

        backend.send()

        self.assertTrue(backend.send_called)

    def test_abstract_send_method(self):
        """Test that _send is abstract and must be implemented."""
        # Create a backend without implementing _send
        class IncompleteBackend(BaseSendBackend):
            PLUGIN_ID = "incomplete"
            PLUGIN_NAME = "Incomplete"
            PLUGIN_DESCRIPTION = "Missing _send"
            CONFIG_FIELDS = []

        # Cannot instantiate abstract class with abstract methods
        with self.assertRaises(TypeError):
            IncompleteBackend({}, {}, 'file.txt')


class TestPluginConfigMixin(unittest.TestCase):
    """Tests for PluginConfigMixin integration."""

    def test_backend_has_config_mixin(self):
        """Test that backend inherits from PluginConfigMixin."""
        backend = MockSendBackend({}, {}, 'file.txt')

        # Should have get_config_fields method from mixin
        self.assertTrue(hasattr(backend, 'get_config_fields'))
        self.assertTrue(callable(getattr(backend, 'get_config_fields')))

    def test_backend_default_config(self):
        """Test getting default config from backend."""
        config = MockSendBackend.get_default_config()

        # Mock backend has empty CONFIG_FIELDS
        self.assertEqual(config, {})


if __name__ == '__main__':
    unittest.main()
