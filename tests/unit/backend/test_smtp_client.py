"""Unit tests for SMTP client implementations."""

import pytest
from unittest.mock import MagicMock, patch
from smtplib import SMTPAuthenticationError
from email.message import EmailMessage

from backend.smtp_client import (
    RealSMTPClient,
    MockSMTPClient,
    create_smtp_client,
)
from backend.protocols import SMTPClientProtocol


class TestRealSMTPClient:
    """Tests for RealSMTPClient implementation."""
    
    @pytest.fixture
    def mock_smtplib(self):
        """Mock smtplib module."""
        with patch('backend.smtp_client.smtplib') as mock:
            mock_smtp = MagicMock()
            mock.SMTP.return_value = mock_smtp
            yield mock
    
    def test_init_default_no_config(self):
        """Test default initialization without config."""
        client = RealSMTPClient()
        assert client.config == {}
        assert client._connection is None
    
    def test_init_with_config(self):
        """Test initialization with config."""
        config = {'host': 'smtp.example.com', 'port': 587}
        client = RealSMTPClient(config=config)
        assert client.config == config
    
    def test_connect_creates_smtp_connection(self, mock_smtplib):
        """Test connect creates SMTP connection."""
        client = RealSMTPClient()
        client.connect('smtp.example.com', 587)
        
        mock_smtplib.SMTP.assert_called_once_with('smtp.example.com', 587)
    
    def test_starttls_delegates_to_connection(self, mock_smtplib):
        """Test starttls delegates to underlying connection."""
        client = RealSMTPClient()
        client.connect('smtp.example.com', 587)
        client.starttls()
        
        mock_smtplib.SMTP.return_value.starttls.assert_called_once()
    
    def test_starttls_raises_when_not_connected(self):
        """Test starttls raises error when not connected."""
        client = RealSMTPClient()
        with pytest.raises(RuntimeError, match="Not connected"):
            client.starttls()
    
    def test_login_delegates_to_connection(self, mock_smtplib):
        """Test login delegates to underlying connection."""
        client = RealSMTPClient()
        client.connect('smtp.example.com', 587)
        client.login('user@example.com', 'password')
        
        mock_smtplib.SMTP.return_value.login.assert_called_once_with(
            'user@example.com', 'password'
        )
    
    def test_login_raises_when_not_connected(self):
        """Test login raises error when not connected."""
        client = RealSMTPClient()
        with pytest.raises(RuntimeError, match="Not connected"):
            client.login('user@example.com', 'password')
    
    def test_sendmail_delegates_to_connection(self, mock_smtplib):
        """Test sendmail delegates to underlying connection."""
        client = RealSMTPClient()
        client.connect('smtp.example.com', 587)
        
        result = client.sendmail(
            'from@example.com',
            ['to@example.com'],
            'Subject: Test\n\nBody'
        )
        
        mock_smtplib.SMTP.return_value.sendmail.assert_called_once()
        assert result == mock_smtplib.SMTP.return_value.sendmail.return_value
    
    def test_sendmail_raises_when_not_connected(self):
        """Test sendmail raises error when not connected."""
        client = RealSMTPClient()
        with pytest.raises(RuntimeError, match="Not connected"):
            client.sendmail('from@example.com', ['to@example.com'], 'msg')
    
    def test_send_message_delegates_to_connection(self, mock_smtplib):
        """Test send_message delegates to underlying connection."""
        client = RealSMTPClient()
        client.connect('smtp.example.com', 587)
        
        msg = EmailMessage()
        msg['Subject'] = 'Test'
        msg['From'] = 'from@example.com'
        msg['To'] = 'to@example.com'
        msg.set_content('Test body')
        
        client.send_message(msg)
        
        mock_smtplib.SMTP.return_value.send_message.assert_called_once_with(msg)
    
    def test_send_message_raises_when_not_connected(self):
        """Test send_message raises error when not connected."""
        client = RealSMTPClient()
        msg = EmailMessage()
        
        with pytest.raises(RuntimeError, match="Not connected"):
            client.send_message(msg)
    
    def test_quit_closes_connection(self, mock_smtplib):
        """Test quit closes connection gracefully."""
        client = RealSMTPClient()
        client.connect('smtp.example.com', 587)
        client.quit()
        
        mock_smtplib.SMTP.return_value.quit.assert_called_once()
        assert client._connection is None
    
    def test_quit_handles_exception(self, mock_smtplib):
        """Test quit handles exceptions gracefully."""
        client = RealSMTPClient()
        client.connect('smtp.example.com', 587)
        mock_smtplib.SMTP.return_value.quit.side_effect = Exception("Connection lost")
        
        # Should not raise
        client.quit()
        assert client._connection is None
    
    def test_close_closes_connection(self, mock_smtplib):
        """Test close closes connection unconditionally."""
        client = RealSMTPClient()
        client.connect('smtp.example.com', 587)
        client.close()
        
        mock_smtplib.SMTP.return_value.close.assert_called_once()
        assert client._connection is None
    
    def test_ehlo_delegates_to_connection(self, mock_smtplib):
        """Test ehlo delegates to underlying connection."""
        client = RealSMTPClient()
        client.connect('smtp.example.com', 587)
        client.ehlo()
        
        mock_smtplib.SMTP.return_value.ehlo.assert_called_once()
    
    def test_ehlo_raises_when_not_connected(self):
        """Test ehlo raises error when not connected."""
        client = RealSMTPClient()
        with pytest.raises(RuntimeError, match="Not connected"):
            client.ehlo()
    
    def test_set_debuglevel_delegates_to_connection(self, mock_smtplib):
        """Test set_debuglevel delegates to underlying connection."""
        client = RealSMTPClient()
        client.connect('smtp.example.com', 587)
        client.set_debuglevel(1)
        
        mock_smtplib.SMTP.return_value.set_debuglevel.assert_called_once_with(1)
    
    def test_connected_property(self, mock_smtplib):
        """Test connected property reflects connection state."""
        client = RealSMTPClient()
        assert not client.connected
        
        client.connect('smtp.example.com', 587)
        assert client.connected
        
        client.close()
        assert not client.connected
    
    def test_from_config_creates_connected_client(self, mock_smtplib):
        """Test from_config creates fully connected client."""
        config = {
            'host': 'smtp.example.com',
            'port': 587,
            'username': 'user@example.com',
            'password': 'password',
            'use_tls': True
        }
        
        client = RealSMTPClient.from_config(config)
        
        mock_smtplib.SMTP.assert_called_once_with('smtp.example.com', 587)
        assert mock_smtplib.SMTP.return_value.starttls.call_count == 1
        mock_smtplib.SMTP.return_value.login.assert_called_once_with(
            'user@example.com', 'password'
        )
    
    def test_from_config_without_auth(self, mock_smtplib):
        """Test from_config without authentication."""
        config = {
            'host': 'smtp.example.com',
            'port': 25,
            'use_tls': False
        }
        
        client = RealSMTPClient.from_config(config)
        
        mock_smtplib.SMTP.return_value.login.assert_not_called()


class TestMockSMTPClient:
    """Tests for MockSMTPClient implementation."""
    
    @pytest.fixture
    def mock_client(self):
        """Create a fresh MockSMTPClient instance."""
        return MockSMTPClient()
    
    def test_init_empty_state(self, mock_client):
        """Test initial state is empty."""
        assert mock_client.connections == []
        assert mock_client.logins == []
        assert mock_client.emails_sent == []
        assert mock_client.starttls_calls == 0
        assert not mock_client._connected
    
    def test_connect_records_connection(self, mock_client):
        """Test connect records connection details."""
        mock_client.connect('smtp.example.com', 587)
        
        assert len(mock_client.connections) == 1
        assert mock_client.connections[0] == ('smtp.example.com', 587)
        assert mock_client._connected
    
    def test_starttls_increments_counter(self, mock_client):
        """Test starttls increments call counter."""
        mock_client.starttls()
        mock_client.starttls()
        
        assert mock_client.starttls_calls == 2
    
    def test_login_records_credentials(self, mock_client):
        """Test login records credentials."""
        mock_client.login('user@example.com', 'password')
        
        assert len(mock_client.logins) == 1
        assert mock_client.logins[0] == ('user@example.com', 'password')
    
    def test_sendmail_records_email(self, mock_client):
        """Test sendmail records email details."""
        result = mock_client.sendmail(
            'from@example.com',
            ['to@example.com'],
            'Subject: Test\n\nBody'
        )
        
        assert len(mock_client.emails_sent) == 1
        email = mock_client.emails_sent[0]
        assert email['from'] == 'from@example.com'
        assert email['to'] == ['to@example.com']
        assert email['type'] == 'raw'
        assert result == {}  # No rejected recipients
    
    def test_send_message_records_email(self, mock_client):
        """Test send_message records EmailMessage."""
        msg = EmailMessage()
        msg['Subject'] = 'Test'
        msg['From'] = 'from@example.com'
        msg['To'] = 'to@example.com'
        msg.set_content('Test body')
        
        result = mock_client.send_message(msg)
        
        assert len(mock_client.emails_sent) == 1
        email = mock_client.emails_sent[0]
        assert email['type'] == 'message'
        assert result == {}
    
    def test_quit_sets_connected_false(self, mock_client):
        """Test quit sets connected to False."""
        mock_client.connect('smtp.example.com', 587)
        assert mock_client._connected
        
        mock_client.quit()
        assert not mock_client._connected
        assert mock_client.quit_called
    
    def test_close_sets_connected_false(self, mock_client):
        """Test close sets connected to False."""
        mock_client.connect('smtp.example.com', 587)
        mock_client.close()
        assert not mock_client._connected
        assert mock_client.close_called
    
    def test_ehlo_increments_counter(self, mock_client):
        """Test ehlo increments call counter."""
        mock_client.ehlo()
        mock_client.ehlo()
        
        assert mock_client.ehlo_calls == 2
    
    def test_set_debuglevel_records_level(self, mock_client):
        """Test set_debuglevel records debug level."""
        mock_client.set_debuglevel(2)
        
        assert mock_client.debug_level == 2
    
    def test_add_error_raises_on_next_operation(self, mock_client):
        """Test add_error raises exception on next operation."""
        mock_client.add_error(SMTPAuthenticationError(535, "Auth failed"))
        
        with pytest.raises(SMTPAuthenticationError):
            mock_client.connect('smtp.example.com', 587)
    
    def test_reset_clears_all_state(self, mock_client):
        """Test reset clears all tracking state."""
        mock_client.connect('smtp.example.com', 587)
        mock_client.login('user', 'pass')
        mock_client.sendmail('from@a.com', ['to@b.com'], 'msg')
        
        mock_client.reset()
        
        assert mock_client.connections == []
        assert mock_client.logins == []
        assert mock_client.emails_sent == []
        assert mock_client.starttls_calls == 0
        assert not mock_client._connected
    
    def test_connected_property(self, mock_client):
        """Test connected property reflects state."""
        assert not mock_client.connected
        mock_client.connect('smtp.example.com', 587)
        assert mock_client.connected
        mock_client.close()
        assert not mock_client.connected


class TestCreateSMTPClient:
    """Tests for create_smtp_client factory function."""
    
    def test_creates_real_client_by_default(self):
        """Test creates RealSMTPClient by default."""
        client = create_smtp_client()
        assert isinstance(client, RealSMTPClient)
    
    def test_creates_real_client_with_config(self):
        """Test creates RealSMTPClient with config."""
        config = {'host': 'smtp.example.com', 'port': 587}
        client = create_smtp_client(config=config)
        assert isinstance(client, RealSMTPClient)
        assert client.config == config
    
    def test_creates_mock_client_when_requested(self):
        """Test creates MockSMTPClient when mock=True."""
        client = create_smtp_client(mock=True)
        assert isinstance(client, MockSMTPClient)


class TestSMTPClientProtocolCompliance:
    """Tests for protocol compliance."""
    
    def test_real_client_implements_protocol(self):
        """Verify RealSMTPClient implements SMTPClientProtocol."""
        client = RealSMTPClient()
        assert isinstance(client, SMTPClientProtocol)
    
    def test_mock_client_implements_protocol(self):
        """Verify MockSMTPClient implements SMTPClientProtocol."""
        client = MockSMTPClient()
        assert isinstance(client, SMTPClientProtocol)
    
    def test_protocol_methods_exist(self):
        """Verify all protocol methods exist on implementations."""
        required_methods = [
            'connect', 'starttls', 'login', 'sendmail',
            'send_message', 'quit', 'close', 'ehlo', 'set_debuglevel'
        ]
        
        for client_class in [RealSMTPClient, MockSMTPClient]:
            client = client_class()
            for method in required_methods:
                assert hasattr(client, method), f"{client_class.__name__} missing {method}"
                assert callable(getattr(client, method)), f"{method} not callable"
