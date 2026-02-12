"""Unit tests for FTP client implementations."""

import io
import pytest
from unittest.mock import MagicMock, patch
from ftplib import error_perm

from backend.ftp_client import (
    RealFTPClient,
    MockFTPClient,
    create_ftp_client,
)
from backend.protocols import FTPClientProtocol


class TestRealFTPClient:
    """Tests for RealFTPClient implementation."""
    
    @pytest.fixture
    def mock_ftplib(self):
        """Mock ftplib module."""
        with patch('backend.ftp_client.ftplib') as mock:
            mock_ftp = MagicMock()
            mock.FTP.return_value = mock_ftp
            mock.FTP_TLS.return_value = mock_ftp
            yield mock
    
    def test_init_default_no_tls(self):
        """Test default initialization without TLS."""
        client = RealFTPClient()
        assert not client.use_tls
        assert client._connection is None
    
    def test_init_with_tls(self):
        """Test initialization with TLS enabled."""
        client = RealFTPClient(use_tls=True)
        assert client.use_tls
        assert client._connection is None
    
    def test_connect_creates_ftp_connection(self, mock_ftplib):
        """Test connect creates FTP connection."""
        client = RealFTPClient(use_tls=False)
        client.connect('ftp.example.com', 21)
        
        mock_ftplib.FTP.assert_called_once()
        mock_ftplib.FTP.return_value.connect.assert_called_once_with(
            'ftp.example.com', 21
        )
    
    def test_connect_creates_ftps_connection_when_tls(self, mock_ftplib):
        """Test connect creates FTP_TLS connection when TLS enabled."""
        client = RealFTPClient(use_tls=True)
        client.connect('ftp.example.com', 990)
        
        mock_ftplib.FTP_TLS.assert_called_once()
        mock_ftplib.FTP_TLS.return_value.connect.assert_called_once_with(
            'ftp.example.com', 990
        )
    
    def test_connect_with_timeout(self, mock_ftplib):
        """Test connect with timeout parameter."""
        client = RealFTPClient()
        client.connect('ftp.example.com', 21, timeout=30.0)
        
        mock_ftplib.FTP.return_value.connect.assert_called_once_with(
            'ftp.example.com', 21, 30.0
        )
    
    def test_login_delegates_to_connection(self, mock_ftplib):
        """Test login delegates to underlying connection."""
        client = RealFTPClient()
        client.connect('ftp.example.com', 21)
        client.login('user', 'password')
        
        mock_ftplib.FTP.return_value.login.assert_called_once_with(
            'user', 'password'
        )
    
    def test_login_raises_when_not_connected(self):
        """Test login raises error when not connected."""
        client = RealFTPClient()
        with pytest.raises(RuntimeError, match="Not connected"):
            client.login('user', 'password')
    
    def test_cwd_delegates_to_connection(self, mock_ftplib):
        """Test cwd delegates to underlying connection."""
        client = RealFTPClient()
        client.connect('ftp.example.com', 21)
        client.cwd('/remote/dir')
        
        mock_ftplib.FTP.return_value.cwd.assert_called_once_with('/remote/dir')
    
    def test_cwd_raises_when_not_connected(self):
        """Test cwd raises error when not connected."""
        client = RealFTPClient()
        with pytest.raises(RuntimeError, match="Not connected"):
            client.cwd('/remote/dir')
    
    def test_storbinary_delegates_to_connection(self, mock_ftplib):
        """Test storbinary delegates to underlying connection."""
        client = RealFTPClient()
        client.connect('ftp.example.com', 21)
        
        fp = io.BytesIO(b'test data')
        client.storbinary('STOR test.txt', fp)
        
        mock_ftplib.FTP.return_value.storbinary.assert_called_once()
    
    def test_storbinary_raises_when_not_connected(self):
        """Test storbinary raises error when not connected."""
        client = RealFTPClient()
        fp = io.BytesIO(b'test data')
        
        with pytest.raises(RuntimeError, match="Not connected"):
            client.storbinary('STOR test.txt', fp)
    
    def test_quit_closes_connection(self, mock_ftplib):
        """Test quit closes connection gracefully."""
        client = RealFTPClient()
        client.connect('ftp.example.com', 21)
        client.quit()
        
        mock_ftplib.FTP.return_value.quit.assert_called_once()
        assert client._connection is None
    
    def test_quit_handles_exception(self, mock_ftplib):
        """Test quit handles exceptions gracefully."""
        client = RealFTPClient()
        client.connect('ftp.example.com', 21)
        mock_ftplib.FTP.return_value.quit.side_effect = Exception("Connection lost")
        
        # Should not raise
        client.quit()
        assert client._connection is None
    
    def test_close_closes_connection(self, mock_ftplib):
        """Test close closes connection unconditionally."""
        client = RealFTPClient()
        client.connect('ftp.example.com', 21)
        client.close()
        
        mock_ftplib.FTP.return_value.close.assert_called_once()
        assert client._connection is None
    
    def test_set_pasv_delegates_to_connection(self, mock_ftplib):
        """Test set_pasv delegates to underlying connection."""
        client = RealFTPClient()
        client.connect('ftp.example.com', 21)
        client.set_pasv(True)
        
        mock_ftplib.FTP.return_value.set_pasv.assert_called_once_with(True)
    
    def test_connected_property(self, mock_ftplib):
        """Test connected property reflects connection state."""
        client = RealFTPClient()
        assert not client.connected
        
        client.connect('ftp.example.com', 21)
        assert client.connected
        
        client.close()
        assert not client.connected


class TestMockFTPClient:
    """Tests for MockFTPClient implementation."""
    
    @pytest.fixture
    def mock_client(self):
        """Create a fresh MockFTPClient instance."""
        return MockFTPClient()
    
    def test_init_empty_state(self, mock_client):
        """Test initial state is empty."""
        assert mock_client.connections == []
        assert mock_client.logins == []
        assert mock_client.files_sent == []
        assert mock_client.directories_changed == []
        assert not mock_client._connected
    
    def test_connect_records_connection(self, mock_client):
        """Test connect records connection details."""
        mock_client.connect('ftp.example.com', 21, timeout=30.0)
        
        assert len(mock_client.connections) == 1
        assert mock_client.connections[0] == ('ftp.example.com', 21, 30.0)
        assert mock_client._connected
    
    def test_login_records_credentials(self, mock_client):
        """Test login records credentials."""
        mock_client.login('testuser', 'testpass')
        
        assert len(mock_client.logins) == 1
        assert mock_client.logins[0] == ('testuser', 'testpass')
    
    def test_cwd_records_directory(self, mock_client):
        """Test cwd records directory change."""
        mock_client.cwd('/remote/dir')
        
        assert len(mock_client.directories_changed) == 1
        assert mock_client.directories_changed[0] == '/remote/dir'
    
    def test_storbinary_records_file_data(self, mock_client):
        """Test storbinary records file data."""
        fp = io.BytesIO(b'test file content')
        mock_client.storbinary('STOR test.txt', fp)
        
        assert len(mock_client.files_sent) == 1
        cmd, data = mock_client.files_sent[0]
        assert cmd == 'STOR test.txt'
        assert data == b'test file content'
    
    def test_storbinary_handles_string_data(self, mock_client):
        """Test storbinary handles string data."""
        fp = io.StringIO('text content')
        mock_client.storbinary('STOR test.txt', fp)
        
        assert len(mock_client.files_sent) == 1
        _, data = mock_client.files_sent[0]
        assert data == b'text content'
    
    def test_quit_sets_connected_false(self, mock_client):
        """Test quit sets connected to False."""
        mock_client.connect('ftp.example.com', 21)
        assert mock_client._connected
        
        mock_client.quit()
        assert not mock_client._connected
    
    def test_close_sets_connected_false(self, mock_client):
        """Test close sets connected to False."""
        mock_client.connect('ftp.example.com', 21)
        mock_client.close()
        assert not mock_client._connected
    
    def test_set_pasv_records_setting(self, mock_client):
        """Test set_pasv records passive mode setting."""
        mock_client.set_pasv(True)
        mock_client.set_pasv(False)
        
        assert mock_client.passive_mode_settings == [True, False]
    
    def test_set_nlst_return_value(self, mock_client):
        """Test set_nlst_return_value configures nlst response."""
        mock_client.set_nlst_return_value(['file1.txt', 'file2.txt'])
        
        result = mock_client.nlst('/remote/dir')
        assert result == ['file1.txt', 'file2.txt']
    
    def test_add_error_raises_on_next_operation(self, mock_client):
        """Test add_error raises exception on next operation."""
        mock_client.add_error(error_perm("Login failed"))
        
        with pytest.raises(error_perm, match="Login failed"):
            mock_client.connect('ftp.example.com', 21)
    
    def test_reset_clears_all_state(self, mock_client):
        """Test reset clears all tracking state."""
        mock_client.connect('ftp.example.com', 21)
        mock_client.login('user', 'pass')
        mock_client.cwd('/dir')
        mock_client.storbinary('STOR test.txt', io.BytesIO(b'data'))
        
        mock_client.reset()
        
        assert mock_client.connections == []
        assert mock_client.logins == []
        assert mock_client.files_sent == []
        assert mock_client.directories_changed == []
        assert not mock_client._connected
    
    def test_connected_property(self, mock_client):
        """Test connected property reflects state."""
        assert not mock_client.connected
        mock_client.connect('ftp.example.com', 21)
        assert mock_client.connected
        mock_client.close()
        assert not mock_client.connected


class TestCreateFTPClient:
    """Tests for create_ftp_client factory function."""
    
    def test_creates_real_client_by_default(self):
        """Test creates RealFTPClient by default."""
        client = create_ftp_client()
        assert isinstance(client, RealFTPClient)
    
    def test_creates_real_client_with_tls(self):
        """Test creates RealFTPClient with TLS option."""
        client = create_ftp_client(use_tls=True)
        assert isinstance(client, RealFTPClient)
        assert client.use_tls
    
    def test_creates_mock_client_when_requested(self):
        """Test creates MockFTPClient when mock=True."""
        client = create_ftp_client(mock=True)
        assert isinstance(client, MockFTPClient)


class TestFTPClientProtocolCompliance:
    """Tests for protocol compliance."""
    
    def test_real_client_implements_protocol(self):
        """Verify RealFTPClient implements FTPClientProtocol."""
        client = RealFTPClient()
        assert isinstance(client, FTPClientProtocol)
    
    def test_mock_client_implements_protocol(self):
        """Verify MockFTPClient implements FTPClientProtocol."""
        client = MockFTPClient()
        assert isinstance(client, FTPClientProtocol)
    
    def test_protocol_methods_exist(self):
        """Verify all protocol methods exist on implementations."""
        required_methods = [
            'connect', 'login', 'cwd', 'storbinary',
            'quit', 'close', 'set_pasv'
        ]
        
        for client_class in [RealFTPClient, MockFTPClient]:
            client = client_class()
            for method in required_methods:
                assert hasattr(client, method), f"{client_class.__name__} missing {method}"
                assert callable(getattr(client, method)), f"{method} not callable"
