"""
Secrets Management for Kuro AI.

Provides centralized secrets access with validation, rotation support,
and secure handling practices.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class SecretType(Enum):
    """Types of secrets managed."""
    API_KEY = "api_key"
    JWT_SECRET = "jwt_secret"
    DATABASE_URL = "database_url"
    ENCRYPTION_KEY = "encryption_key"
    WEBHOOK_SECRET = "webhook_secret"
    OAUTH_CLIENT_SECRET = "oauth_client_secret"


@dataclass
class SecretMetadata:
    """Metadata about a secret."""
    name: str
    secret_type: SecretType
    required: bool = True
    description: str = ""
    pattern: Optional[str] = None  # Regex pattern for validation
    rotation_days: int = 90  # Recommended rotation period
    last_rotated: Optional[str] = None  # ISO timestamp


# Secret registry - defines all secrets the application needs
SECRET_REGISTRY: Dict[str, SecretMetadata] = {
    "GROQ_API_KEY": SecretMetadata(
        name="GROQ_API_KEY",
        secret_type=SecretType.API_KEY,
        required=True,
        description="Groq API key for LLM inference",
        pattern=r"^gsk_[a-zA-Z0-9]{48}$",
        rotation_days=90,
    ),
    "OPENAI_API_KEY": SecretMetadata(
        name="OPENAI_API_KEY",
        secret_type=SecretType.API_KEY,
        required=False,
        description="OpenAI API key (via OpenRouter)",
        pattern=r"^sk-[a-zA-Z0-9]{48}$",
        rotation_days=90,
    ),
    "OPENROUTER_API_KEY": SecretMetadata(
        name="OPENROUTER_API_KEY",
        secret_type=SecretType.API_KEY,
        required=False,
        description="OpenRouter API key for multi-provider access",
        pattern=r"^sk-or-[a-zA-Z0-9]{32,}$",
        rotation_days=90,
    ),
    "CLERK_SECRET_KEY": SecretMetadata(
        name="CLERK_SECRET_KEY",
        secret_type=SecretType.JWT_SECRET,
        required=True,
        description="Clerk secret key for JWT verification",
        pattern=r"^sk_(test|live)_[a-zA-Z0-9]{32,}$",
        rotation_days=180,
    ),
    "CLERK_PUBLISHABLE_KEY": SecretMetadata(
        name="CLERK_PUBLISHABLE_KEY",
        secret_type=SecretType.API_KEY,
        required=True,
        description="Clerk publishable key for frontend",
        pattern=r"^pk_(test|live)_[a-zA-Z0-9]{32,}$",
        rotation_days=180,
    ),
    "MONGODB_URI": SecretMetadata(
        name="MONGODB_URI",
        secret_type=SecretType.DATABASE_URL,
        required=True,
        description="MongoDB connection string",
        pattern=r"^mongodb(\+srv)?://",
        rotation_days=180,
    ),
    "PINECONE_API_KEY": SecretMetadata(
        name="PINECONE_API_KEY",
        secret_type=SecretType.API_KEY,
        required=True,
        description="Pinecone API key for vector storage",
        pattern=r"^[a-zA-Z0-9]{8}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{12}$",
        rotation_days=180,
    ),
    "PINECONE_INDEX_NAME": SecretMetadata(
        name="PINECONE_INDEX_NAME",
        secret_type=SecretType.API_KEY,
        required=False,
        description="Pinecone index name",
        rotation_days=365,
    ),
    "GEMINI_API_KEY": SecretMetadata(
        name="GEMINI_API_KEY",
        secret_type=SecretType.API_KEY,
        required=True,
        description="Google Gemini API key for embeddings",
        pattern=r"^AIza[a-zA-Z0-9_-]{35}$",
        rotation_days=90,
    ),
    "JWT_SECRET": SecretMetadata(
        name="JWT_SECRET",
        secret_type=SecretType.JWT_SECRET,
        required=False,
        description="Fallback JWT secret for internal tokens",
        pattern=r"^[a-zA-Z0-9+/=]{32,}$",
        rotation_days=90,
    ),
    "ENCRYPTION_MASTER_KEY": SecretMetadata(
        name="ENCRYPTION_MASTER_KEY",
        secret_type=SecretType.ENCRYPTION_KEY,
        required=True,
        description="Master encryption key for data at rest",
        pattern=r"^[a-zA-Z0-9+/=]{44}$",  # Base64 encoded 32 bytes
        rotation_days=365,
    ),
    "WEBHOOK_SECRET": SecretMetadata(
        name="WEBHOOK_SECRET",
        secret_type=SecretType.WEBHOOK_SECRET,
        required=False,
        description="Secret for webhook signature verification",
        pattern=r"^[a-zA-Z0-9]{32,}$",
        rotation_days=90,
    ),
    "SENTRY_DSN": SecretMetadata(
        name="SENTRY_DSN",
        secret_type=SecretType.API_KEY,
        required=False,
        description="Sentry DSN for error tracking",
        pattern=r"^https://[a-zA-Z0-9]+@[a-zA-Z0-9]+\.ingest\.sentry\.io/\d+",
        rotation_days=180,
    ),
    "REDIS_URL": SecretMetadata(
        name="REDIS_URL",
        secret_type=SecretType.DATABASE_URL,
        required=False,
        description="Redis connection URL for caching/rate limiting",
        pattern=r"^redis://",
        rotation_days=180,
    ),
}


class SecretsManager:
    """Centralized secrets management with validation and caching."""

    def __init__(self):
        self._cache: Dict[str, str] = {}
        self._validation_results: Dict[str, bool] = {}
        self._load_all()

    def _load_all(self) -> None:
        """Load and validate all registered secrets."""
        for name, metadata in SECRET_REGISTRY.items():
            value = os.getenv(name)
            if value is None:
                if metadata.required:
                    logger.error(f"Required secret missing: {name} ({metadata.description})")
                    self._validation_results[name] = False
                else:
                    logger.warning(f"Optional secret not set: {name} ({metadata.description})")
                    self._validation_results[name] = True
                continue

            # Validate pattern if provided
            if metadata.pattern and not re.match(metadata.pattern, value):
                logger.error(f"Secret {name} does not match expected pattern")
                self._validation_results[name] = False
                continue

            self._cache[name] = value
            self._validation_results[name] = True
            logger.debug(f"Loaded secret: {name}")

    def get(self, name: str) -> Optional[str]:
        """Get a secret value by name."""
        if name not in SECRET_REGISTRY:
            logger.warning(f"Requested unknown secret: {name}")
            return None
        return self._cache.get(name)

    def require(self, name: str) -> str:
        """Get a required secret, raising if not available."""
        value = self.get(name)
        if value is None:
            metadata = SECRET_REGISTRY.get(name)
            raise ValueError(f"Required secret not available: {name} ({metadata.description if metadata else 'unknown'})")
        return value

    def is_valid(self, name: str) -> bool:
        """Check if a secret is valid and available."""
        return self._validation_results.get(name, False)

    def all_valid(self) -> bool:
        """Check if all required secrets are valid."""
        return all(
            self._validation_results.get(name, False)
            for name, meta in SECRET_REGISTRY.items()
            if meta.required
        )

    def get_missing_required(self) -> List[str]:
        """Get list of missing required secrets."""
        return [
            name for name, meta in SECRET_REGISTRY.items()
            if meta.required and not self._validation_results.get(name, False)
        ]

    def get_validation_report(self) -> Dict[str, Any]:
        """Get full validation report."""
        return {
            "all_valid": self.all_valid(),
            "missing_required": self.get_missing_required(),
            "details": {
                name: {
                    "valid": self._validation_results.get(name, False),
                    "required": meta.required,
                    "type": meta.secret_type.value,
                    "description": meta.description,
                }
                for name, meta in SECRET_REGISTRY.items()
            }
        }

    def get_redacted_config(self) -> Dict[str, str]:
        """Get configuration with secrets redacted for logging."""
        redacted = {}
        for name in SECRET_REGISTRY:
            value = self._cache.get(name)
            if value:
                # Show first 4 and last 4 chars
                if len(value) > 8:
                    redacted[name] = f"{value[:4]}...{value[-4:]}"
                else:
                    redacted[name] = "****"
            else:
                redacted[name] = "<not set>"
        return redacted


# Global instance
_secrets_manager: Optional[SecretsManager] = None


def get_secrets_manager() -> SecretsManager:
    """Get global secrets manager instance."""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager


def get_secret(name: str) -> Optional[str]:
    """Convenience function to get a secret."""
    return get_secrets_manager().get(name)


def require_secret(name: str) -> str:
    """Convenience function to require a secret."""
    return get_secrets_manager().require(name)


def validate_secrets() -> Dict[str, Any]:
    """Validate all secrets and return report."""
    return get_secrets_manager().get_validation_report()


__all__ = [
    "SecretType",
    "SecretMetadata",
    "SecretsManager",
    "SECRET_REGISTRY",
    "get_secrets_manager",
    "get_secret",
    "require_secret",
    "validate_secrets",
]