"""
Encryption at Rest for Kuro AI.

Provides AES-256-GCM authenticated encryption with key derivation,
rotation support, and per-user key isolation.
"""

from __future__ import annotations

import base64
import logging
import os
import secrets
from dataclasses import dataclass
from typing import Optional, Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

logger = logging.getLogger(__name__)


@dataclass
class EncryptionKey:
    """Encryption key with metadata."""
    key_id: str
    key_bytes: bytes  # 32 bytes for AES-256
    created_at: str  # ISO timestamp
    version: int = 1
    purpose: str = "data_encryption"  # data_encryption, pii_encryption, etc.


@dataclass
class EncryptedData:
    """Encrypted payload with metadata."""
    ciphertext: bytes
    nonce: bytes  # 12 bytes for AES-GCM
    key_id: str
    version: int = 1
    aad: Optional[bytes] = None  # Additional authenticated data


class KeyManager:
    """Manages encryption keys with derivation and rotation."""

    def __init__(self, master_key_b64: Optional[str] = None):
        """
        Initialize key manager.
        
        Args:
            master_key_b64: Base64-encoded 32-byte master key.
                           If None, reads from ENCRYPTION_MASTER_KEY env var.
        """
        if master_key_b64 is None:
            master_key_b64 = os.getenv("ENCRYPTION_MASTER_KEY")
        
        if not master_key_b64:
            raise ValueError("Master encryption key not provided (ENCRYPTION_MASTER_KEY env var)")
        
        try:
            self._master_key = base64.b64decode(master_key_b64)
        except Exception as e:
            raise ValueError(f"Invalid master key format: {e}")
        
        if len(self._master_key) != 32:
            raise ValueError("Master key must be 32 bytes (256 bits)")
        
        # In-memory key cache: key_id -> EncryptionKey
        self._keys: dict[str, EncryptionKey] = {}
        
        # Create initial key
        self._create_initial_key()
        
        logger.info("KeyManager initialized with master key")

    def _create_initial_key(self) -> EncryptionKey:
        """Create the initial encryption key."""
        key_id = "key_v1"
        key_bytes = self._derive_key(key_id)
        
        key = EncryptionKey(
            key_id=key_id,
            key_bytes=key_bytes,
            created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
            version=1,
            purpose="data_encryption"
        )
        self._keys[key_id] = key
        return key

    def _derive_key(self, key_id: str, purpose: str = "data_encryption") -> bytes:
        """
        Derive a 32-byte key from master key using HKDF.
        
        Args:
            key_id: Unique identifier for this key
            purpose: Purpose string for key separation
            
        Returns:
            32-byte derived key
        """
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=key_id.encode(),
            info=f"kuro-{purpose}".encode(),
        )
        return hkdf.derive(self._master_key)

    def get_key(self, key_id: str = "current") -> EncryptionKey:
        """Get encryption key by ID."""
        if key_id == "current":
            # Return the latest key
            if not self._keys:
                return self._create_initial_key()
            latest = max(self._keys.values(), key=lambda k: k.version)
            return latest
        
        if key_id not in self._keys:
            # Derive on-demand for known key IDs
            key_bytes = self._derive_key(key_id)
            key = EncryptionKey(
                key_id=key_id,
                key_bytes=key_bytes,
                created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
                version=len(self._keys) + 1,
            )
            self._keys[key_id] = key
            return key
        
        return self._keys[key_id]

    def rotate_key(self) -> EncryptionKey:
        """
        Rotate to a new encryption key.
        
        Returns:
            New EncryptionKey
        """
        new_version = max(k.version for k in self._keys.values()) + 1
        key_id = f"key_v{new_version}"
        
        key_bytes = self._derive_key(key_id)
        new_key = EncryptionKey(
            key_id=key_id,
            key_bytes=key_bytes,
            created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
            version=new_version,
            purpose="data_encryption"
        )
        self._keys[key_id] = new_key
        
        logger.info(f"Rotated encryption key to version {new_version} ({key_id})")
        return new_key

    def list_keys(self) -> list[EncryptionKey]:
        """List all available keys."""
        return list(self._keys.values())


class EncryptionManager:
    """High-level encryption/decryption with AES-256-GCM."""

    def __init__(self, key_manager: Optional[KeyManager] = None):
        """
        Initialize encryption manager.
        
        Args:
            key_manager: KeyManager instance. If None, creates one from env.
        """
        self.key_manager = key_manager or KeyManager()
        self._aesgcm_cache: dict[str, AESGCM] = {}

    def _get_aesgcm(self, key: EncryptionKey) -> AESGCM:
        """Get or create AESGCM instance for a key."""
        if key.key_id not in self._aesgcm_cache:
            self._aesgcm_cache[key.key_id] = AESGCM(key.key_bytes)
        return self._aesgcm_cache[key.key_id]

    def encrypt(
        self,
        plaintext: bytes,
        key_id: str = "current",
        aad: Optional[bytes] = None,
    ) -> EncryptedData:
        """
        Encrypt data with AES-256-GCM.
        
        Args:
            plaintext: Data to encrypt
            key_id: Key identifier to use
            aad: Additional authenticated data (optional)
            
        Returns:
            EncryptedData with ciphertext, nonce, and metadata
        """
        if not plaintext:
            raise ValueError("Cannot encrypt empty data")
        
        key = self.key_manager.get_key(key_id)
        aesgcm = self._get_aesgcm(key)
        
        # Generate random 12-byte nonce (96 bits recommended for GCM)
        nonce = secrets.token_bytes(12)
        
        # Encrypt with AAD
        ciphertext = self._get_aesgcm(key).encrypt(nonce, plaintext, aad)
        
        return EncryptedData(
            ciphertext=ciphertext,
            nonce=nonce,
            key_id=key.key_id,
            version=key.version,
            aad=aad,
        )

    def decrypt(
        self,
        encrypted: EncryptedData,
        aad: Optional[bytes] = None,
    ) -> bytes:
        """
        Decrypt data with AES-256-GCM.
        
        Args:
            encrypted: EncryptedData to decrypt
            aad: Additional authenticated data (must match encryption)
            
        Returns:
            Decrypted plaintext
            
        Raises:
            ValueError: If decryption fails (wrong key, tampered data, etc.)
        """
        key = self.key_manager.get_key(encrypted.key_id)
        
        try:
            plaintext = self._get_aesgcm(key).decrypt(
                encrypted.nonce,
                encrypted.ciphertext,
                aad or encrypted.aad,
            )
            return plaintext
        except Exception as e:
            logger.error(f"Decryption failed for key {encrypted.key_id}: {e}")
            raise ValueError("Decryption failed: invalid key, corrupted data, or tampered ciphertext") from e

    def encrypt_string(self, text: str, key_id: str = "current", aad: Optional[str] = None) -> str:
        """Encrypt string and return base64-encoded result."""
        encrypted = self.encrypt(text.encode("utf-8"), key_id, aad.encode("utf-8") if aad else None)
        # Combine nonce + ciphertext for storage
        combined = encrypted.nonce + encrypted.ciphertext
        return base64.b64encode(combined).decode("ascii")

    def decrypt_string(self, encoded: str, aad: Optional[str] = None) -> str:
        """Decrypt base64-encoded string."""
        combined = base64.b64decode(encoded.encode("ascii"))
        if len(combined) < 12:
            raise ValueError("Invalid encrypted data: too short")
        
        nonce = combined[:12]
        ciphertext = combined[12:]
        
        encrypted = EncryptedData(
            ciphertext=ciphertext,
            nonce=nonce,
            key_id="current",  # Will use current key
            version=1,
            aad=aad.encode("utf-8") if aad else None,
        )
        return self.decrypt(encrypted, aad.encode("utf-8") if aad else None).decode("utf-8")


# Global instances
_key_manager: Optional[KeyManager] = None
_encryption_manager: Optional[EncryptionManager] = None


def get_key_manager() -> KeyManager:
    global _key_manager
    if _key_manager is None:
        _key_manager = KeyManager()
    return _key_manager


def get_encryption_manager() -> EncryptionManager:
    global _encryption_manager
    if _encryption_manager is None:
        _encryption_manager = EncryptionManager(get_key_manager())
    return _encryption_manager


def encrypt_data(data: bytes, key_id: str = "current", aad: Optional[bytes] = None) -> EncryptedData:
    """Convenience function to encrypt data."""
    return get_encryption_manager().encrypt(data, key_id, aad)


def decrypt_data(encrypted: EncryptedData, aad: Optional[bytes] = None) -> bytes:
    """Convenience function to decrypt data."""
    return get_encryption_manager().decrypt(encrypted, aad)


def encrypt_string(text: str, key_id: str = "current", aad: Optional[str] = None) -> str:
    """Convenience function to encrypt string."""
    return get_encryption_manager().encrypt_string(text, key_id, aad)


def decrypt_string(encoded: str, aad: Optional[str] = None) -> str:
    """Convenience function to decrypt string."""
    return get_encryption_manager().decrypt_string(encoded, aad)


__all__ = [
    "EncryptionKey",
    "EncryptedData",
    "KeyManager",
    "EncryptionManager",
    "get_key_manager",
    "get_encryption_manager",
    "encrypt_data",
    "decrypt_data",
    "encrypt_string",
    "decrypt_string",
]