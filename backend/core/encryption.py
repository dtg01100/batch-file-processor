"""
Encryption utilities for secure password storage
"""

import base64
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    logger.warning("cryptography not available, install with: pip install cryptography")


class EncryptionManager:
    """Manages encryption/decryption of sensitive data"""

    def __init__(self, secret_key: Optional[str] = None):
        """
        Initialize encryption manager

        Args:
            secret_key: Secret key for encryption (from env or generated)
        """
        if not CRYPTO_AVAILABLE:
            raise Exception("cryptography not installed")

        # Get or generate encryption key
        if secret_key:
            self.key = self._derive_key(secret_key)
        else:
            self.key = self._generate_key()
            logger.warning(
                "Generated temporary encryption key - set SECRET_KEY in production!"
            )

        self.cipher = Fernet(self.key)

    def _derive_key(self, password: str) -> bytes:
        """Derive encryption key from password"""
        # Use PBKDF2 to derive a 32-byte key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"batch_file_processor_salt",  # In production, use random salt
            iterations=100000,
        )
        key = kdf.derive(password.encode())
        # Return base64-encoded key for Fernet
        return base64.urlsafe_b64encode(key)

    def _generate_key(self) -> bytes:
        """Generate a random encryption key"""
        return Fernet.generate_key()

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext string

        Args:
            plaintext: String to encrypt

        Returns:
            Base64-encoded encrypted string
        """
        try:
            encrypted_bytes = self.cipher.encrypt(plaintext.encode())
            # Fernet already returns base64-encoded bytes
            return encrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise Exception(f"Encryption failed: {e}")

    def decrypt(self, encrypted: str) -> str:
        """
        Decrypt encrypted string

        Args:
            encrypted: Base64-encoded encrypted string

        Returns:
            Decrypted plaintext string
        """
        try:
            # Fernet expects base64-encoded bytes, not raw bytes
            encrypted_bytes = encrypted.encode()
            decrypted_bytes = self.cipher.decrypt(encrypted_bytes)
            return decrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise Exception(f"Decryption failed: {e}")


# Global encryption manager instance
_encryption_manager: Optional[EncryptionManager] = None


def get_encryption_manager() -> EncryptionManager:
    """Get or create global encryption manager"""
    global _encryption_manager

    if _encryption_manager is None:
        secret_key = os.environ.get("SECRET_KEY")
        _encryption_manager = EncryptionManager(secret_key)

    return _encryption_manager


def encrypt_password(password: str) -> str:
    """Encrypt a password"""
    return get_encryption_manager().encrypt(password)


def decrypt_password(encrypted: str) -> str:
    """Decrypt a password"""
    return get_encryption_manager().decrypt(encrypted)
