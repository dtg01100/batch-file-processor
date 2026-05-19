"""Tests for dispatch.services.database_connector module."""

from unittest.mock import MagicMock, patch

import pytest

from core.database.query_runner import QueryRunner
from dispatch.services.database_connector import DatabaseConnector


class TestDatabaseConnector:
    """Tests for DatabaseConnector class."""

    def test_init_connection_success(self):
        """Valid settings create QueryRunner and set is_initialized."""
        mock_query_runner = MagicMock(spec=QueryRunner)
        with patch(
            "core.database.query_runner.create_query_runner_from_settings",
            return_value=mock_query_runner,
        ) as mock_create:
            connector = DatabaseConnector()
            connector.init_connection(
                {
                    "as400_username": "user",
                    "as400_password": "pass",
                    "as400_address": "host",
                }
            )

            assert connector.is_initialized is True
            assert connector.query_runner is mock_query_runner
            mock_create.assert_called_once_with(
                {"as400_username": "user", "as400_password": "pass", "as400_address": "host"},
                database="QGPL",
            )

    def test_init_connection_missing_keys_raises_value_error(self):
        """Missing required keys raises ValueError with key names."""
        connector = DatabaseConnector()
        with pytest.raises(ValueError, match="as400_address"):
            connector.init_connection(
                {
                    "as400_username": "user",
                    "as400_password": "pass",
                }
            )

    def test_init_connection_missing_both_password_and_key_raises(self):
        """Empty password and no ssh_key_filename raises ValueError."""
        connector = DatabaseConnector()
        with pytest.raises(
            ValueError,
            match="Either as400_password or ssh_key_filename must be provided",
        ):
            connector.init_connection(
                {
                    "as400_username": "user",
                    "as400_address": "host",
                    "as400_password": "",
                    "ssh_key_filename": "",
                }
            )

    def test_init_connection_with_ssh_key_only(self):
        """Key-only auth works with empty password but valid ssh_key_filename."""
        mock_query_runner = MagicMock(spec=QueryRunner)
        with patch(
            "core.database.query_runner.create_query_runner_from_settings",
            return_value=mock_query_runner,
        ) as mock_create:
            connector = DatabaseConnector()
            connector.init_connection(
                {
                    "as400_username": "user",
                    "as400_password": "",
                    "as400_address": "host",
                    "ssh_key_filename": "/tmp/key.pem",
                }
            )

            assert connector.is_initialized is True
            assert connector.query_runner is mock_query_runner
            assert connector.ssh_key_filename == "/tmp/key.pem"
            assert connector.as400_password is None
            mock_create.assert_called_once()

    def test_double_init_is_no_op(self):
        """Second init_connection call does not create a new QueryRunner."""
        mock_query_runner = MagicMock(spec=QueryRunner)
        with patch(
            "core.database.query_runner.create_query_runner_from_settings",
            return_value=mock_query_runner,
        ) as mock_create:
            connector = DatabaseConnector()
            connector.init_connection(
                {
                    "as400_username": "user",
                    "as400_password": "pass",
                    "as400_address": "host",
                }
            )

            assert mock_create.call_count == 1

            connector.init_connection(
                {
                    "as400_username": "wrong",
                    "as400_password": "wrong",
                    "as400_address": "wrong",
                }
            )

            assert mock_create.call_count == 1
            assert connector.query_runner is mock_query_runner

    def test_close_closes_query_runner(self):
        """close() calls query_runner.close() and resets state."""
        mock_query_runner = MagicMock(spec=QueryRunner)
        with patch(
            "core.database.query_runner.create_query_runner_from_settings",
            return_value=mock_query_runner,
        ):
            connector = DatabaseConnector()
            connector.init_connection(
                {
                    "as400_username": "user",
                    "as400_password": "pass",
                    "as400_address": "host",
                }
            )

            connector.close()

            mock_query_runner.close.assert_called_once()
            assert connector.is_initialized is False
            assert connector.query_runner is None

    def test_close_safe_when_not_initialized(self):
        """close() when not connected does not raise."""
        connector = DatabaseConnector()
        connector.close()
        assert connector.query_runner is None
        assert connector.is_initialized is False

    def test_close_safe_when_query_runner_close_raises(self):
        """close() handles AttributeError from query_runner.close gracefully."""
        mock_query_runner = MagicMock(spec=QueryRunner)
        mock_query_runner.close.side_effect = AttributeError("already closed")
        with patch(
            "core.database.query_runner.create_query_runner_from_settings",
            return_value=mock_query_runner,
        ):
            connector = DatabaseConnector()
            connector.init_connection(
                {
                    "as400_username": "user",
                    "as400_password": "pass",
                    "as400_address": "host",
                }
            )

            connector.close()

            mock_query_runner.close.assert_called_once()
            assert connector.is_initialized is False
            assert connector.query_runner is None
