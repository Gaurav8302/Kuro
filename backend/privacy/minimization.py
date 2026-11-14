"""
Data Minimization and Retention for Kuro AI.

Provides PII redaction for logs/metrics and automated data lifecycle management.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Pattern, Set
from enum import Enum

logger = logging.getLogger(__name__)


class DataCategory(Enum):
    """Categories of data for retention policies."""
    CHAT_MESSAGES = "chat_messages"
    USER_PROFILE = "user_profile"
    MEMORY_VECTORS = "memory_vectors"
    SESSION_METADATA = "session_metadata"
    AUDIT_LOGS = "audit_logs"
    METRICS = "metrics"
    ERROR_LOGS = "error_logs"
    PROVIDER_LOGS = "provider_logs"


@dataclass
class RetentionPolicy:
    """Retention policy for a data category."""
    category: DataCategory
    retention_days: int
    grace_period_days: int = 7  # Soft delete grace period
    description: str = ""
    legal_basis: str = "legitimate_interest"  # GDPR legal basis


# Default retention policies
DEFAULT_RETENTION_POLICIES: Dict[DataCategory, RetentionPolicy] = {
    DataCategory.CHAT_MESSAGES: RetentionPolicy(
        category=DataCategory.CHAT_MESSAGES,
        retention_days=365,
        grace_period_days=30,
        description="User chat history",
        legal_basis="contract",
    ),
    DataCategory.USER_PROFILE: RetentionPolicy(
        category=DataCategory.USER_PROFILE,
        retention_days=2555,  # 7 years
        grace_period_days=90,
        description="User profile data",
        legal_basis="contract",
    ),
    DataCategory.MEMORY_VECTORS: RetentionPolicy(
        category=DataCategory.MEMORY_VECTORS,
        retention_days=730,  # 2 years
        grace_period_days=30,
        description="Long-term memory embeddings",
        legal_basis="legitimate_interest",
    ),
    DataCategory.SESSION_METADATA: RetentionPolicy(
        category=DataCategory.SESSION_METADATA,
        retention_days=365,
        grace_period_days=7,
        description="Session IDs, titles, timestamps",
        legal_basis="legitimate_interest",
    ),
    DataCategory.AUDIT_LOGS: RetentionPolicy(
        category=DataCategory.AUDIT_LOGS,
        retention_days=2555,  # 7 years for compliance
        grace_period_days=0,
        description="Security and access audit logs",
        legal_basis="legal_obligation",
    ),
    DataCategory.METRICS: RetentionPolicy(
        category=DataCategory.METRICS,
        retention_days=90,
        grace_period_days=0,
        description="Aggregated system metrics",
        legal_basis="legitimate_interest",
    ),
    DataCategory.ERROR_LOGS: RetentionPolicy(
        category=DataCategory.ERROR_LOGS,
        retention_days=90,
        grace_period_days=0,
        description="Application error logs",
        legal_basis="legitimate_interest",
    ),
    DataCategory.PROVIDER_LOGS: RetentionPolicy(
        category=DataCategory.PROVIDER_LOGS,
        retention_days=30,
        grace_period_days=0,
        description="LLM provider request/response logs",
        legal_basis="legitimate_interest",
    ),
}


# PII detection patterns
PII_PATTERNS: Dict[str, Pattern] = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    "phone": re.compile(r"\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),
    "api_key_gsk": re.compile(r"\bgsk_[a-zA-Z0-9]{48}\b"),
    "api_key_sk": re.compile(r"\bsk-[a-zA-Z0-9]{32,}\b"),
    "api_key_sk_or": re.compile(r"\bsk-or-[a-zA-Z0-9]{32,}\b"),
    "api_key_pk": re.compile(r"\bpk_[a-zA-Z0-9]{32,}\b"),
    "jwt_token": re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
    "mongodb_uri": re.compile(r"mongodb(\+srv)?://[^\s]+"),
    "ipv4": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "uuid": re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"),
}


@dataclass
class RedactionResult:
    """Result of PII redaction."""
    redacted_text: str
    findings: List[Dict[str, Any]]
    original_length: int
    redacted_length: int


class DataMinimizer:
    """Redacts PII from text for logging and metrics."""

    def __init__(
        self,
        custom_patterns: Optional[Dict[str, Pattern]] = None,
        replacement: str = "[REDACTED]",
    ):
        """
        Initialize data minimizer.
        
        Args:
            custom_patterns: Additional regex patterns for redaction
            replacement: Replacement string for matches
        """
        self.patterns = {**PII_PATTERNS}
        if custom_patterns:
            self.patterns.update(custom_patterns)
        self.replacement = replacement

    def redact(self, text: str) -> RedactionResult:
        """
        Redact PII from text.
        
        Args:
            text: Text to redact
            
        Returns:
            RedactionResult with redacted text and findings
        """
        if not text:
            return RedactionResult(
                redacted_text="",
                findings=[],
                original_length=0,
                redacted_length=0,
            )

        findings = []
        redacted = text
        offset = 0  # Track offset changes due to redaction length differences

        for pattern_name, pattern in self.patterns.items():
            for match in pattern.finditer(text):
                start, end = match.span()
                matched_text = match.group()
                
                # Adjust for previous redactions
                adj_start = start + offset
                adj_end = end + offset
                
                # Replace in redacted text
                redacted = redacted[:adj_start] + self.replacement + redacted[adj_end:]
                
                # Update offset
                offset += len(self.replacement) - (end - start)
                
                findings.append({
                    "type": pattern_name,
                    "original_position": {"start": start, "end": end},
                    "matched_length": len(matched_text),
                })

        return RedactionResult(
            redacted_text=redacted,
            findings=findings,
            original_length=len(text),
            redacted_length=len(redacted),
        )

    def redact_dict(self, data: Dict[str, Any], keys_to_redact: Optional[Set[str]] = None) -> Dict[str, Any]:
        """
        Redact sensitive keys from dictionary.
        
        Args:
            data: Dictionary to redact
            keys_to_redact: Set of key names to redact (default: common sensitive keys)
            
        Returns:
            Redacted dictionary
        """
        if keys_to_redact is None:
            keys_to_redact = {
                "password", "secret", "token", "api_key", "apikey",
                "authorization", "auth", "credential", "key",
                "email", "phone", "ssn", "address",
                "user_id", "session_id", "device_id",
            }

        redacted = {}
        for key, value in data.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in keys_to_redact):
                if isinstance(value, str) and value:
                    result = self.redact(value)
                    redacted[key] = result.redacted_text
                else:
                    redacted[key] = self.replacement
            elif isinstance(value, dict):
                redacted[key] = self.redact_dict(value, keys_to_redact)
            elif isinstance(value, list):
                redacted[key] = [
                    self.redact_dict(item, keys_to_redact) if isinstance(item, dict)
                    else self.redact(str(item)).redacted_text if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                redacted[key] = value

        return redacted


class RetentionManager:
    """Manages data retention and deletion lifecycle."""

    def __init__(
        self,
        policies: Optional[Dict[DataCategory, RetentionPolicy]] = None,
    ):
        """
        Initialize retention manager.
        
        Args:
            policies: Custom retention policies (uses defaults if not provided)
        """
        self.policies = policies or DEFAULT_RETENTION_POLICIES
        self._deletion_log: List[Dict[str, Any]] = []

    def get_policy(self, category: DataCategory) -> RetentionPolicy:
        """Get retention policy for category."""
        return self.policies.get(category, RetentionPolicy(
            category=category,
            retention_days=365,
            description=f"Default policy for {category.value}",
        ))

    def is_expired(self, category: DataCategory, created_at: datetime) -> bool:
        """Check if data has exceeded retention period."""
        policy = self.get_policy(category)
        expiry = created_at + timedelta(days=policy.retention_days)
        return datetime.now(timezone.utc) > expiry

    def is_in_grace_period(self, category: DataCategory, deleted_at: datetime) -> bool:
        """Check if soft-deleted data is in grace period."""
        policy = self.get_policy(category)
        grace_end = deleted_at + timedelta(days=policy.grace_period_days)
        return datetime.now(timezone.utc) < grace_end

    def get_retention_info(self, category: DataCategory, created_at: datetime) -> Dict[str, Any]:
        """Get retention information for a data item."""
        policy = self.get_policy(category)
        expiry = created_at + timedelta(days=policy.retention_days)
        now = datetime.now(timezone.utc)
        
        return {
            "category": category.value,
            "created_at": created_at.isoformat(),
            "expires_at": expiry.isoformat(),
            "days_remaining": max(0, (expiry - now).days),
            "is_expired": now > expiry,
            "retention_days": policy.retention_days,
            "grace_period_days": policy.grace_period_days,
            "legal_basis": policy.legal_basis,
        }

    def log_deletion(
        self,
        category: DataCategory,
        user_id: str,
        data_identifiers: List[str],
        deletion_type: str = "hard",  # "soft" or "hard"
        reason: str = "retention_policy",
    ) -> None:
        """Log a deletion for audit trail."""
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "category": category.value,
            "user_id": user_id,
            "data_identifiers": data_identifiers,
            "deletion_type": deletion_type,
            "reason": reason,
            "policy_retention_days": self.get_policy(category).retention_days,
        }
        self._deletion_log.append(log_entry)
        logger.info(f"Data deletion logged: {log_entry}")

    def get_deletion_log(
        self,
        user_id: Optional[str] = None,
        category: Optional[DataCategory] = None,
        since: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Get deletion audit log."""
        logs = self._deletion_log
        if user_id:
            logs = [l for l in logs if l["user_id"] == user_id]
        if category:
            logs = [l for l in logs if l["category"] == category.value]
        if since:
            logs = [l for l in logs if datetime.fromisoformat(l["timestamp"]) > since]
        return logs


# Global instances
_data_minimizer: Optional[DataMinimizer] = None
_retention_manager: Optional[RetentionManager] = None


def get_data_minimizer() -> DataMinimizer:
    global _data_minimizer
    if _data_minimizer is None:
        _data_minimizer = DataMinimizer()
    return _data_minimizer


def get_retention_manager() -> RetentionManager:
    global _retention_manager
    if _retention_manager is None:
        _retention_manager = RetentionManager()
    return _retention_manager


def redact_text(text: str) -> str:
    """Convenience function to redact text."""
    return get_data_minimizer().redact(text).redacted_text


def redact_dict(data: Dict[str, Any], keys_to_redact: Optional[Set[str]] = None) -> Dict[str, Any]:
    """Convenience function to redact dict."""
    return get_data_minimizer().redact_dict(data, keys_to_redact)


def check_retention(category: DataCategory, created_at: datetime) -> Dict[str, Any]:
    """Convenience function to check retention status."""
    return get_retention_manager().get_retention_info(category, created_at)


def log_data_deletion(
    category: DataCategory,
    user_id: str,
    data_identifiers: List[str],
    deletion_type: str = "hard",
    reason: str = "retention_policy",
) -> None:
    """Convenience function to log deletion."""
    get_retention_manager().log_deletion(category, user_id, data_identifiers, deletion_type, reason)


__all__ = [
    "DataCategory",
    "RetentionPolicy",
    "DEFAULT_RETENTION_POLICIES",
    "PII_PATTERNS",
    "RedactionResult",
    "DataMinimizer",
    "RetentionManager",
    "get_data_minimizer",
    "get_retention_manager",
    "redact_text",
    "redact_dict",
    "check_retention",
    "log_data_deletion",
]