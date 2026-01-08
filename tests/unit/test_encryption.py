"""
Unit tests for encryption utilities
"""

import pytest
import os
from backend.core.encryption import (
    EncryptionManager,
    encrypt_password,
    decrypt_password,
    get_encryption_manager,
)


class TestEncryptionManager:
    """Tests for EncryptionManager"""

    def test_generate_key(self):
        """Test key generation"""
        # Clear any existing manager
        from backend.core import encryption

        encryption._encryption_manager = None

        manager = EncryptionManager()
        assert manager.key is not None
        assert len(manager.key) > 0

    def test_encrypt_decrypt(self):
        """Test encryption and decryption"""
        # Clear any existing manager
        from backend.core import encryption

        encryption._encryption_manager = None

        manager = EncryptionManager()
        plaintext = "test_password_123"

        # Encrypt
        encrypted = manager.encrypt(plaintext)
        assert encrypted != plaintext
        assert "gAAA" in encrypted  # Fernet encrypted strings start with 'gAAA'

        # Decrypt
        decrypted = manager.decrypt(encrypted)
        assert decrypted == plaintext

    def test_encrypted_password_not_reversible(self):
        """Test that encrypted password is not plaintext"""
        from backend.core import encryption

        encryption._encryption_manager = None

        manager = EncryptionManager()
        plaintext = "my_secret_password"
        encrypted = manager.encrypt(plaintext)

        assert encrypted != plaintext
        # Should not be possible to reverse the encryption without key
        assert plaintext not in encrypted

    def test_encrypt_with_custom_key(self):
        """Test encryption with custom secret key"""
        from backend.core import encryption

        encryption._encryption_manager = None

        manager = EncryptionManager(secret_key="custom_secret_key_123")
        plaintext = "test_message"

        encrypted = manager.encrypt(plaintext)
        decrypted = manager.decrypt(encrypted)

        assert decrypted == plaintext


class TestConvenienceFunctions:
    """Tests for convenience encryption functions"""

    def test_encrypt_password_function(self):
        """Test encrypt_password convenience function"""
        # Set secret key
        os.environ["SECRET_KEY"] = "test_key_123456"

        from backend.core import encryption

        encryption._encryption_manager = None

        password = "my_password"
        encrypted = encrypt_password(password)

        assert encrypted != password
        assert "gAAA" in encrypted

    def test_decrypt_password_function(self):
        """Test decrypt_password convenience function"""
        os.environ["SECRET_KEY"] = "test_key_123456"

        from backend.core import encryption

        encryption._encryption_manager = None

        password = "my_password"
        encrypted = encrypt_password(password)
        decrypted = decrypt_password(encrypted)

        assert decrypted == password

    def test_get_encryption_manager_singleton(self):
        """Test that get_encryption_manager returns singleton"""
        os.environ["SECRET_KEY"] = "test_key"

        from backend.core import encryption

        encryption._encryption_manager = None

        manager1 = get_encryption_manager()
        manager2 = get_encryption_manager()

        assert manager1 is manager2
