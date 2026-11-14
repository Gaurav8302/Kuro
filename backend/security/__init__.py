"""
Security package for Kuro AI.

Provides authentication, secrets management, and encryption at rest.
"""

from .auth import (
    ClerkJWKSVerifier,
    AuthenticatedPrincipal,
    get_current_principal,
    require_admin,
    require_service_token,
    set_test_public_key,
    get_test_private_key,
    get_test_public_key,
)

from .secrets import (
    SecretType,
    SecretMetadata,
    SecretsManager,
    SECRET_REGISTRY,
    get_secrets_manager,
    get_secret,
    require_secret,
    validate_secrets,
)

from .encryption import (
    EncryptionKey,
    EncryptedData,
    KeyManager,
    EncryptionManager,
    get_key_manager,
    get_encryption_manager,
    encrypt_data,
    decrypt_data,
    encrypt_string,
    decrypt_string,
)

__all__ = [
    # auth
    "ClerkJWKSVerifier",
    "AuthPrincipal",
    "get_current_principal",
    "require_admin",
    "require_service_token",
    "set_test_public_key",
    "get_test_private_key",
    "get_test_public_key",
    # secrets
    "SecretType",
    "SecretMetadata",
    "SecretsManager",
    "SECRET_REGISTRY",
    "get_secrets_manager",
    "get_secret",
    "require_secret",
    "validate_secrets",
    # encryption
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