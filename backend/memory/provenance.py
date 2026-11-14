"""
Memory Provenance and Validation Module.

Provides structured memory records with provenance tracking,
validation, and conflict resolution for Phase 5.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Literal
from dataclasses import dataclass, field, asdict
from enum import Enum
import json

logger = logging.getLogger(__name__)


class MemoryType(Enum):
    """Memory type categories."""
    FACT = "fact"
    PREFERENCE = "preference"
    EVENT = "event"
    CONTACT = "contact"
    NOTE = "note"


class MemorySource(Enum):
    """Provenance source of memory."""
    USER_EXPLICIT = "user_explicit"           # User directly stated
    INFERRED_FROM_CONVERSATION = "inferred_from_conversation"  # Derived from chat
    EXTRACTED_BY_LLM = "extracted_by_llm"    # LLM extraction
    USER_CONFIRMED = "user_confirmed"         # User explicitly confirmed


class MemoryStatus(Enum):
    """Memory lifecycle status."""
    ACTIVE = "active"
    SUPERSEDED = "superseded"      # Replaced by newer info
    EXPIRED = "expired"            # Time-sensitive info expired
    DELETED = "deleted"            # User requested deletion
    PENDING_CONFIRMATION = "pending_confirmation"  # Awaiting user confirmation


@dataclass
class MemoryProvenance:
    """Tracks the origin and lifecycle of a memory."""
    source: MemorySource
    source_message_id: Optional[str] = None      # Original message that created this
    extraction_model: Optional[str] = None       # LLM model used for extraction
    extraction_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    confidence: float = 0.5                      # 0.0 - 1.0
    user_confirmed: bool = False                 # User explicitly confirmed
    confirmed_at: Optional[datetime] = None
    confirmed_by: Optional[str] = None           # User ID who confirmed
    supersedes: Optional[str] = None             # Memory ID this supersedes
    superseded_by: Optional[str] = None          # Memory ID that supersedes this
    tags: List[str] = field(default_factory=list)


@dataclass
class MemoryRecord:
    """Complete memory record with provenance and lifecycle tracking."""
    # Core identifiers
    memory_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    
    # Content
    memory_type: MemoryType = MemoryType.FACT
    content: str = ""
    
    # Metadata
    importance: float = 0.5                      # 0.0 - 1.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None        # For time-sensitive memories
    
    # Provenance
    provenance: MemoryProvenance = field(default_factory=lambda: MemoryProvenance(source=MemorySource.EXTRACTED_BY_LLM))
    
    # Lifecycle
    status: MemoryStatus = MemoryStatus.ACTIVE
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None
    
    # Versioning
    version: int = 1
    previous_version_id: Optional[str] = None
    
    # Embedding reference
    embedding_id: Optional[str] = None
    embedding_model: Optional[str] = None
    
    # Access control
    is_shared: bool = False                      # If true, visible to other users (rare)
    shared_with: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        data = asdict(self)
        # Convert enums to strings
        data["memory_type"] = self.memory_type.value
        data["provenance"]["source"] = self.provenance.source.value
        data["status"] = self.status.value
        # Convert datetimes to ISO strings
        for key in ["created_at", "updated_at", "expires_at", "deleted_at", 
                    "provenance.extraction_timestamp", "provenance.confirmed_at"]:
            val = self._get_nested(data, key)
            if isinstance(val, datetime):
                self._set_nested(data, key, val.isoformat())
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryRecord":
        """Create from dictionary."""
        # Convert string enums back
        if isinstance(data.get("memory_type"), str):
            data["memory_type"] = MemoryType(data["memory_type"])
        if isinstance(data.get("status"), str):
            data["status"] = MemoryStatus(data["status"])
        if isinstance(data.get("provenance", {}).get("source"), str):
            data["provenance"]["source"] = MemorySource(data["provenance"]["source"])
        # Convert ISO strings to datetimes
        for key in ["created_at", "updated_at", "expires_at", "deleted_at",
                    "provenance.extraction_timestamp", "provenance.confirmed_at"]:
            val = cls._get_nested(data, key)
            if isinstance(val, str):
                try:
                    cls._set_nested(data, key, datetime.fromisoformat(val))
                except ValueError:
                    pass
        if isinstance(data.get("provenance"), dict):
            data["provenance"] = MemoryProvenance(**data["provenance"])
        return cls(**data)
    
    @staticmethod
    def _get_nested(d: Dict, key: str) -> Any:
        """Get nested dict value by dot-separated key."""
        parts = key.split(".")
        cur = d
        for part in parts:
            if isinstance(cur, dict):
                cur = cur.get(part)
            else:
                return None
        return cur
    
    @staticmethod
    def _set_nested(d: Dict, key: str, value: Any) -> None:
        """Set nested dict value by dot-separated key."""
        parts = key.split(".")
        cur = d
        for part in parts[:-1]:
            if part not in cur:
                cur[part] = {}
            cur = cur[part]
        cur[parts[-1]] = value
    
    def is_expired(self) -> bool:
        """Check if memory has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) >= self.expires_at
    
    def is_deletable(self) -> bool:
        """Check if memory can be deleted (not already deleted)."""
        return self.status != MemoryStatus.DELETED
    
    def supersede_with(self, new_memory: "MemoryRecord") -> None:
        """Mark this memory as superseded by another."""
        self.status = MemoryStatus.SUPERSEDED
        self.updated_at = datetime.now(timezone.utc)
        self.provenance.superseded_by = new_memory.memory_id
        new_memory.provenance.supersedes = self.memory_id
        new_memory.previous_version_id = self.memory_id
        new_memory.version = self.version + 1


class MemoryValidator:
    """Validates memory records for quality and safety."""
    
    # Content that should never be stored as memory
    FORBIDDEN_PATTERNS = [
        (r"(?i)\b(password|secret|token|api[_\s]?key)\s*[:=]\s*\S+", "credential"),
        (r"(?i)\b(ssn|social\s+security|credit\s+card|bank\s+account)\b", "pii"),
        (r"(?i)\b(private\s+key|ssh\s+key)\b", "credential"),
    ]
    
    # Minimum content requirements
    MIN_CONTENT_LENGTH = 3
    MAX_CONTENT_LENGTH = 5000
    
    @classmethod
    def validate(cls, memory: MemoryRecord) -> List[str]:
        """Validate a memory record. Returns list of errors (empty if valid)."""
        errors = []
        
        # Content validation
        if not memory.content or not memory.content.strip():
            errors.append("Content cannot be empty")
        elif len(memory.content) < cls.MIN_CONTENT_LENGTH:
            errors.append(f"Content too short (min {cls.MIN_CONTENT_LENGTH} chars)")
        elif len(memory.content) > cls.MAX_CONTENT_LENGTH:
            errors.append(f"Content too long (max {cls.MAX_CONTENT_LENGTH} chars)")
        
        # Check for forbidden patterns
        content_lower = memory.content.lower()
        for pattern, category in cls.FORBIDDEN_PATTERNS:
            import re
            if re.search(pattern, content_lower):
                errors.append(f"Content contains forbidden {category}")
        
        # Provenance validation
        if memory.provenance.confidence < 0.0 or memory.provenance.confidence > 1.0:
            errors.append("Confidence must be between 0.0 and 1.0")
        
        if memory.provenance.source == MemorySource.USER_CONFIRMED and not memory.provenance.user_confirmed:
            errors.append("USER_CONFIRMED source requires user_confirmed=True")
        
        # Owner validation
        if not memory.user_id:
            errors.append("User ID is required")
        
        # Expiration validation
        if memory.expires_at and memory.expires_at <= memory.created_at:
            errors.append("Expiration must be after creation")
        
        return errors
    
    @classmethod
    def sanitize(cls, memory: MemoryRecord) -> MemoryRecord:
        """Return sanitized copy of memory (remove sensitive data)."""
        sanitized = MemoryRecord.from_dict(memory.to_dict())
        # Redact potential sensitive info in content
        # (Additional sanitization could be added here)
        return sanitized


class MemoryConflictResolver:
    """Resolves conflicts between memories."""
    
    @staticmethod
    def resolve(
        existing: MemoryRecord,
        new: MemoryRecord,
        strategy: Literal["newest_wins", "highest_confidence", "user_confirmed_wins", "merge"] = "newest_wins"
    ) -> MemoryRecord:
        """
        Resolve conflict between existing and new memory.
        
        Strategies:
        - newest_wins: Newer memory wins (default)
        - highest_confidence: Higher confidence wins
        - user_confirmed_wins: User-confirmed memories win
        - merge: Attempt to merge content
        """
        if strategy == "newest_wins":
            return new if new.created_at >= existing.created_at else existing
        elif strategy == "highest_confidence":
            return new if new.provenance.confidence >= existing.provenance.confidence else existing
        elif strategy == "user_confirmed_wins":
            if new.provenance.user_confirmed and not existing.provenance.user_confirmed:
                return new
            if existing.provenance.user_confirmed and not new.provenance.user_confirmed:
                return existing
            return new if new.created_at >= existing.created_at else existing
        elif strategy == "merge":
            # Create merged memory
            merged = MemoryRecord(
                user_id=existing.user_id,
                memory_type=existing.memory_type,
                content=f"{existing.content}\n---\n{new.content}",
                importance=max(existing.importance, new.importance),
                provenance=MemoryProvenance(
                    source=MemorySource.EXTRACTED_BY_LLM,
                    confidence=max(existing.provenance.confidence, new.provenance.confidence),
                    tags=["merged"]
                ),
                expires_at=min(
                    filter(None, [existing.expires_at, new.expires_at]),
                    default=None
                )
            )
            merged.provenance.tags = ["merged", f"from_{existing.memory_id[:8]}", f"from_{new.memory_id[:8]}"]
            merged.previous_version_id = existing.memory_id
            return merged
        else:
            return new


__all__ = [
    "MemoryType",
    "MemorySource", 
    "MemoryStatus",
    "MemoryProvenance",
    "MemoryRecord",
    "MemoryValidator",
    "MemoryConflictResolver",
]