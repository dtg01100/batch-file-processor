"""
Comprehensive unit tests for query_runner.py module.

Tests the query_runner class for database query execution functionality.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

import pytest

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import query_runner as query_runner_module
from query_runner import query_runner


class TestQueryRunnerImport(unittest.TestCase):
    """Tests for query_runner module import and HAS_PYODBC flag."""
    
    def test_has_pyodbc_flag_exists(self):
        """Test HAS_PYODBC flag exists."""
        self.assertTrue(hasattr(query_runner_module, 'HAS_PYODBC'))
    
    def test_pyodbc_import(self):
        """Test pyodbc module handling."""
        # Should have pyodbc attribute (either real or None)
        self.assertTrue(hasattr(query_runner_module, 'pyodbc'))


class TestQueryRunnerInit(unittest.TestCase):
    """Tests for query_runner initialization."""
    
    @patch.object(query_runner_module, 'HAS_PYODBC', False)
    def test_init_without_pyodbc_raises(self):
        """Test initialization raises RuntimeError when pyodbc unavailable."""
        with self.assertRaises(RuntimeError) as context:
            query_runner('user', 'pass', 'host', 'driver')
        
        self.assertIn("pyodbc not available", str(context.exception))
    
    @patch.object(query_runner_module, 'HAS_PYODBC', True)
    @patch.object(query_runner_module, 'pyodbc')
    def test_init_with_pyodbc(self, mock_pyodbc):
        """Test successful initialization with pyodbc."""
        mock_connection = MagicMock()
        mock_pyodbc.connect.return_value = mock_connection
        
        qr = query_runner('test_user', 'test_pass', 'test_host', 'test_driver')
        
        self.assertIsNotNone(qr)
        self.assertEqual(qr.connection, mock_connection)
        self.assertEqual(qr.username, "")
        self.assertEqual(qr.password, "")
        self.assertEqual(qr.host, "")
        
        # Verify connection was made with correct parameters
        mock_pyodbc.connect.assert_called_once_with(
            driver='test_driver',
            system='test_host',
            uid='test_user',
            pwd='test_pass',
            p_str=None
        )
    
    @patch.object(query_runner_module, 'HAS_PYODBC', True)
    @patch.object(query_runner_module, 'pyodbc')
    def test_init_stores_empty_credentials(self, mock_pyodbc):
        """Test that credentials are cleared after connection."""
        mock_pyodbc.connect.return_value = MagicMock()
        
        qr = query_runner('user', 'pass', 'host', 'driver')
        
        # Credentials should be cleared for security
        self.assertEqual(qr.username, "")
        self.assertEqual(qr.password, "")
        self.assertEqual(qr.host, "")


class TestRunArbitraryQuery(unittest.TestCase):
    """Tests for run_arbitrary_query method."""
    
    @patch.object(query_runner_module, 'HAS_PYODBC', False)
    def test_run_query_without_pyodbc_raises(self):
        """Test run_arbitrary_query raises when pyodbc unavailable."""
        with self.assertRaises(RuntimeError) as context:
            # Need to mock init to bypass pyodbc check
            with patch.object(query_runner_module, 'HAS_PYODBC', True):
                with patch.object(query_runner_module, 'pyodbc'):
                    qr = query_runner('u', 'p', 'h', 'd')
            
            # Now test with HAS_PYODBC=False
            with patch.object(query_runner_module, 'HAS_PYODBC', False):
                qr.run_arbitrary_query("SELECT * FROM test")
        
        # The exception might be raised in init or in run_arbitrary_query
        pass  # Just verify no crash
    
    @patch.object(query_runner_module, 'HAS_PYODBC', True)
    @patch.object(query_runner_module, 'pyodbc')
    def test_run_query_success(self, mock_pyodbc):
        """Test successful query execution."""
        # Setup mock cursor and results
        mock_cursor = MagicMock()
        mock_cursor.execute.return_value = [
            ('row1_col1', 'row1_col2'),
            ('row2_col1', 'row2_col2'),
        ]
        
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_pyodbc.connect.return_value = mock_connection
        
        qr = query_runner('user', 'pass', 'host', 'driver')
        result = qr.run_arbitrary_query("SELECT * FROM test_table")
        
        # Verify cursor was created
        mock_connection.cursor.assert_called_once()
        # Verify query was executed
        mock_cursor.execute.assert_called_once_with("SELECT * FROM test_table")
        # Verify results were returned
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], ('row1_col1', 'row1_col2'))
    
    @patch.object(query_runner_module, 'HAS_PYODBC', True)
    @patch.object(query_runner_module, 'pyodbc')
    def test_run_query_empty_result(self, mock_pyodbc):
        """Test query returning empty result set."""
        mock_cursor = MagicMock()
        mock_cursor.execute.return_value = []
        
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_pyodbc.connect.return_value = mock_connection
        
        qr = query_runner('user', 'pass', 'host', 'driver')
        result = qr.run_arbitrary_query("SELECT * FROM empty_table")
        
        self.assertEqual(result, [])
    
    @patch.object(query_runner_module, 'HAS_PYODBC', True)
    @patch.object(query_runner_module, 'pyodbc')
    def test_run_query_single_row(self, mock_pyodbc):
        """Test query returning single row."""
        mock_cursor = MagicMock()
        mock_cursor.execute.return_value = [('single_value',)]
        
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_pyodbc.connect.return_value = mock_connection
        
        qr = query_runner('user', 'pass', 'host', 'driver')
        result = qr.run_arbitrary_query("SELECT count(*) FROM test")
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], ('single_value',))
    
    @patch.object(query_runner_module, 'HAS_PYODBC', True)
    @patch.object(query_runner_module, 'pyodbc')
    def test_run_query_multiple_columns(self, mock_pyodbc):
        """Test query returning multiple columns."""
        mock_cursor = MagicMock()
        mock_cursor.execute.return_value = [
            ('col1_val', 'col2_val', 'col3_val', 123, 456.78),
        ]
        
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_pyodbc.connect.return_value = mock_connection
        
        qr = query_runner('user', 'pass', 'host', 'driver')
        result = qr.run_arbitrary_query("SELECT * FROM multi_col_table")
        
        self.assertEqual(len(result[0]), 5)
        self.assertEqual(result[0][3], 123)


class TestQueryRunnerIntegration(unittest.TestCase):
    """Integration-style tests for query_runner."""
    
    @patch.object(query_runner_module, 'HAS_PYODBC', True)
    @patch.object(query_runner_module, 'pyodbc')
    def test_multiple_queries_same_connection(self, mock_pyodbc):
        """Test running multiple queries on same connection."""
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = [
            [('result1',)],
            [('result2',)],
            [('result3',)],
        ]
        
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_pyodbc.connect.return_value = mock_connection
        
        qr = query_runner('user', 'pass', 'host', 'driver')
        
        # Run multiple queries
        r1 = qr.run_arbitrary_query("QUERY 1")
        r2 = qr.run_arbitrary_query("QUERY 2")
        r3 = qr.run_arbitrary_query("QUERY 3")
        
        # Each should return different results
        self.assertEqual(r1, [('result1',)])
        self.assertEqual(r2, [('result2',)])
        self.assertEqual(r3, [('result3',)])
        
        # Cursor should be created for each query
        self.assertEqual(mock_connection.cursor.call_count, 3)
    
    @patch.object(query_runner_module, 'HAS_PYODBC', True)
    @patch.object(query_runner_module, 'pyodbc')
    def test_complex_query(self, mock_pyodbc):
        """Test with complex SQL query."""
        mock_cursor = MagicMock()
        mock_cursor.execute.return_value = [
            (1, 'Item A', 100.50),
            (2, 'Item B', 200.75),
        ]
        
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_pyodbc.connect.return_value = mock_connection
        
        qr = query_runner('user', 'pass', 'host', 'driver')
        
        complex_query = """
            SELECT 
                item_id,
                item_name,
                price
            FROM 
                inventory
            WHERE 
                category = 'ELECTRONICS'
                AND price > 50.00
            ORDER BY 
                price DESC
        """
        
        result = qr.run_arbitrary_query(complex_query)
        
        mock_cursor.execute.assert_called_once_with(complex_query)
        self.assertEqual(len(result), 2)


class TestQueryRunnerEdgeCases(unittest.TestCase):
    """Edge case tests for query_runner."""

    @patch.object(query_runner_module, 'HAS_PYODBC', True)
    @patch.object(query_runner_module, 'pyodbc')
    def test_query_with_special_characters(self, mock_pyodbc):
        """Test query with special characters."""
        mock_cursor = MagicMock()
        mock_cursor.execute.return_value = []

        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_pyodbc.connect.return_value = mock_connection

        qr = query_runner('user', 'pass', 'host', 'driver')

        special_query = "SELECT * FROM test WHERE name LIKE '%test%_%'"
        qr.run_arbitrary_query(special_query)

        mock_cursor.execute.assert_called_once_with(special_query)

    @patch.object(query_runner_module, 'HAS_PYODBC', True)
    @patch.object(query_runner_module, 'pyodbc')
    def test_query_with_unicode(self, mock_pyodbc):
        """Test query with unicode characters."""
        mock_cursor = MagicMock()
        mock_cursor.execute.return_value = []

        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_pyodbc.connect.return_value = mock_connection

        qr = query_runner('user', 'pass', 'host', 'driver')

        unicode_query = "SELECT * FROM test WHERE name = '日本語'"
        qr.run_arbitrary_query(unicode_query)

        mock_cursor.execute.assert_called_once_with(unicode_query)


if __name__ == '__main__':
    unittest.main()
