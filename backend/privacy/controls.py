"""
User Data Controls for Kuro AI.

Implements GDPR/CCPA user rights:
- Right to Access (Article 15)
- Right to Rectification (Article 16)
- Right to Erasure (Article 17)
- Right to Restrict Processing (Article 18)
- Right to Data Portability (Article 20)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from enum import Enum

logger = logging.getLogger(__name__)


class DataControlAction(Enum):
    """User data control actions."""
    EXPORT = "export"           # Article 15/20 - Access and portability
    DELETE = "delete"           # Article 17 - Right to erasure
    RECTIFY = "rectify"         # Article 16 - Right to rectification
    RESTRICT = "restrict"       # Article 18 - Right to restrict processing
    ACCESS_LOG = "access_log"   # Article 15 - Access to processing logs


@dataclass
class DataExportRequest:
    """Request for data export."""
    user_id: str
    requested_at: str
    categories: List[str]  # Data categories to include
    format: str = "json"  # json, csv
    status: str = "pending"
    completed_at: Optional[str] = None
    download_url: Optional[str] = None
    expires_at: Optional[str] = None


@dataclass
class DataDeletionRequest:
    """Request for data deletion."""
    user_id: str
    requested_at: str
    categories: List[str]  # Data categories to delete
    confirm: bool = False  # Must be true for actual deletion
    status: str = "pending"
    completed_at: Optional[str] = None
    items_deleted: Dict[str, int] = field(default_factory=dict)  # category -> count


@dataclass
class RectificationRequest:
    """Request for data rectification."""
    user_id: str
    requested_at: str
    corrections: Dict[str, Any]  # field -> new_value
    status: str = "pending"
    completed_at: Optional[str] = None
    fields_updated: List[str] = field(default_factory=list)


@dataclass
class RestrictionRequest:
    """Request for processing restriction."""
    user_id: str
    requested_at: str
    categories: List[str]  # Categories to restrict
    reason: str
    status: str = "pending"
    completed_at: Optional[str] = None


class UserDataController:
    """
    Controller for user data rights operations.
    
    Coordinates with database, vector store, and other systems
    to fulfill user data requests.
    """

    def __init__(
        self,
        db_client=None,
        vector_client=None,
        session_manager=None,
        memory_manager=None,
    ):
        """
        Initialize user data controller.
        
        Args:
            db_client: MongoDB client (optional)
            vector_client: Pinecone client (optional)
            session_manager: Session manager (optional)
            memory_manager: Memory manager (optional)
        """
        self.db_client = db_client
        self.vector_client = vector_client
        self.session_manager = session_manager
        self.memory_manager = memory_manager
        
        # In-memory request tracking (use DB in production)
        self._export_requests: Dict[str, DataExportRequest] = {}
        self._deletion_requests: Dict[str, DataDeletionRequest] = {}
        self._rectification_requests: Dict[str, RectificationRequest] = {}
        self._restriction_requests: Dict[str, RestrictionRequest] = {}

    # =========================================================================
    # EXPORT / ACCESS (GDPR Articles 15, 20)
    # =========================================================================

    async def export_user_data(
        self,
        user_id: str,
        categories: Optional[List[str]] = None,
        format: str = "json",
    ) -> Dict[str, Any]:
        """
        Export all user data for portability/access rights.
        
        Args:
            user_id: User identifier
            categories: Data categories to export (None = all)
            format: Export format (json, csv)
            
        Returns:
            Export data structure
        """
        if categories is None:
            categories = [
                "profile", "sessions", "messages", "memories",
                "preferences", "audit_logs", "provider_usage"
            ]

        export_data = {
            "export_metadata": {
                "user_id": user_id,
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "format": format,
                "categories": categories,
                "version": "1.0",
            }
        }

        # Export profile
        if "profile" in categories:
            export_data["profile"] = await self._export_profile(user_id)

        # Export sessions
        if "sessions" in categories:
            sessions = await self._export_sessions(user_id)
            export_data["sessions"] = {"items": sessions, "count": len(sessions)}  # type: ignore[assignment]

        # Export messages
        if "messages" in categories:
            messages = await self._export_messages(user_id)
            export_data["messages"] = {"items": messages, "count": len(messages)}  # type: ignore[assignment]

        # Export memories
        if "memories" in categories:
            memories = await self._export_memories(user_id)
            export_data["memories"] = {"items": memories, "count": len(memories)}  # type: ignore[assignment]

        # Export preferences
        if "preferences" in categories:
            export_data["preferences"] = await self._export_preferences(user_id)

        # Export audit logs
        if "audit_logs" in categories:
            audit_logs = await self._export_audit_logs(user_id)
            export_data["audit_logs"] = {"items": audit_logs, "count": len(audit_logs)}  # type: ignore[assignment]

        # Export provider usage
        if "provider_usage" in categories:
            provider_usage = await self._export_provider_usage(user_id)
            export_data["provider_usage"] = {"items": provider_usage, "count": len(provider_usage)}  # type: ignore[assignment]

        return export_data

    async def _export_profile(self, user_id: str) -> Dict[str, Any]:
        """Export user profile data."""
        if self.db_client:
            try:
                profile = await self.db_client.users.find_one({"user_id": user_id})
                if profile:
                    profile.pop("_id", None)
                    return profile
            except Exception as e:
                logger.error(f"Failed to export profile for {user_id}: {e}")
        return {}

    async def _export_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Export user sessions."""
        if self.db_client:
            try:
                sessions = await self.db_client.sessions.find(
                    {"user_id": user_id}
                ).to_list(length=None)
                for s in sessions:
                    s.pop("_id", None)
                return sessions
            except Exception as e:
                logger.error(f"Failed to export sessions for {user_id}: {e}")
        return []

    async def _export_messages(self, user_id: str) -> List[Dict[str, Any]]:
        """Export user messages."""
        if self.db_client:
            try:
                # Get user's session IDs first
                session_ids = [
                    s["session_id"] 
                    for s in await self.db_client.sessions.find(
                        {"user_id": user_id}, {"session_id": 1}
                    ).to_list(length=None)
                ]
                if session_ids:
                    messages = await self.db_client.messages.find(
                        {"session_id": {"$in": session_ids}}
                    ).to_list(length=None)
                    for m in messages:
                        m.pop("_id", None)
                    return messages
            except Exception as e:
                logger.error(f"Failed to export messages for {user_id}: {e}")
        return []

    async def _export_memories(self, user_id: str) -> List[Dict[str, Any]]:
        """Export user memories from vector store."""
        if self.vector_client:
            try:
                # Query vectors by user_id metadata
                results = self.vector_client.query_vectors(
                    user_id=user_id,
                    top_k=10000,  # Large number to get all
                    include_metadata=True,
                )
                memories = []
                for match in results.get("matches", []):
                    mem = match.get("metadata", {})
                    mem["vector_id"] = match.get("id")
                    mem["score"] = match.get("score")
                    memories.append(mem)
                return memories
            except Exception as e:
                logger.error(f"Failed to export memories for {user_id}: {e}")
        return []

    async def _export_preferences(self, user_id: str) -> Dict[str, Any]:
        """Export user preferences."""
        if self.db_client:
            try:
                prefs = await self.db_client.preferences.find_one({"user_id": user_id})
                if prefs:
                    prefs.pop("_id", None)
                    return prefs
            except Exception as e:
                logger.error(f"Failed to export preferences for {user_id}: {e}")
        return {}

    async def _export_audit_logs(self, user_id: str) -> List[Dict[str, Any]]:
        """Export user audit logs."""
        if self.db_client:
            try:
                logs = await self.db_client.audit_logs.find(
                    {"user_id": user_id}
                ).sort("timestamp", -1).limit(1000).to_list(length=None)
                for log in logs:
                    log.pop("_id", None)
                return logs
            except Exception as e:
                logger.error(f"Failed to export audit logs for {user_id}: {e}")
        return []

    async def _export_provider_usage(self, user_id: str) -> List[Dict[str, Any]]:
        """Export provider usage logs."""
        if self.db_client:
            try:
                logs = await self.db_client.provider_logs.find(
                    {"user_id": user_id}
                ).sort("timestamp", -1).limit(1000).to_list(length=None)
                for log in logs:
                    log.pop("_id", None)
                return logs
            except Exception as e:
                logger.error(f"Failed to export provider logs for {user_id}: {e}")
        return []

    def create_export_request(
        self,
        user_id: str,
        categories: Optional[List[str]] = None,
        format: str = "json",
    ) -> DataExportRequest:
        """Create a tracked export request."""
        request = DataExportRequest(
            user_id=user_id,
            requested_at=datetime.now(timezone.utc).isoformat(),
            categories=categories or [
                "profile", "sessions", "messages", "memories",
                "preferences", "audit_logs", "provider_usage"
            ],
            format=format,
        )
        request_id = f"export_{user_id}_{int(datetime.now(timezone.utc).timestamp())}"
        self._export_requests[request_id] = request
        return request

    # =========================================================================
    # DELETION / ERASURE (GDPR Article 17)
    # =========================================================================

    async def delete_user_data(
        self,
        user_id: str,
        categories: Optional[List[str]] = None,
        confirm: bool = False,
    ) -> Dict[str, int]:
        """
        Delete user data (right to erasure).
        
        Args:
            user_id: User identifier
            categories: Data categories to delete (None = all)
            confirm: Must be True to actually delete
            
        Returns:
            Dict of category -> count of items deleted
        """
        if not confirm:
            raise ValueError("Deletion requires explicit confirmation (confirm=True)")

        if categories is None:
            categories = [
                "messages", "sessions", "memories", "memories_vectors",
                "profile", "preferences", "audit_logs", "provider_logs"
            ]

        deleted_counts = {}

        # Delete messages
        if "messages" in categories:
            deleted_counts["messages"] = await self._delete_messages(user_id)

        # Delete sessions
        if "sessions" in categories:
            deleted_counts["sessions"] = await self._delete_sessions(user_id)

        # Delete memory vectors
        if "memories_vectors" in categories:
            deleted_counts["memories_vectors"] = await self._delete_memory_vectors(user_id)

        # Delete memories (metadata)
        if "memories" in categories:
            deleted_counts["memories"] = await self._delete_memories(user_id)

        # Delete profile
        if "profile" in categories:
            deleted_counts["profile"] = await self._delete_profile(user_id)

        # Delete preferences
        if "preferences" in categories:
            deleted_counts["preferences"] = await self._delete_preferences(user_id)

        # Delete audit logs
        if "audit_logs" in categories:
            deleted_counts["audit_logs"] = await self._delete_audit_logs(user_id)

        # Delete provider logs
        if "provider_logs" in categories:
            deleted_counts["provider_logs"] = await self._delete_provider_logs(user_id)

        logger.info(f"Deleted user data for {user_id}: {deleted_counts}")
        return deleted_counts

    async def _delete_messages(self, user_id: str) -> int:
        """Delete user messages."""
        if self.db_client:
            try:
                session_ids = [
                    s["session_id"] 
                    for s in await self.db_client.sessions.find(
                        {"user_id": user_id}, {"session_id": 1}
                    ).to_list(length=None)
                ]
                if session_ids:
                    result = await self.db_client.messages.delete_many(
                        {"session_id": {"$in": session_ids}}
                    )
                    return result.deleted_count
            except Exception as e:
                logger.error(f"Failed to delete messages for {user_id}: {e}")
        return 0

    async def _delete_sessions(self, user_id: str) -> int:
        """Delete user sessions."""
        if self.db_client:
            try:
                result = await self.db_client.sessions.delete_many({"user_id": user_id})
                return result.deleted_count
            except Exception as e:
                logger.error(f"Failed to delete sessions for {user_id}: {e}")
        return 0

    async def _delete_memory_vectors(self, user_id: str) -> int:
        """Delete user memory vectors from Pinecone."""
        if self.vector_client:
            try:
                # Delete by user_id metadata filter
                self.vector_client.delete_user_vectors(user_id)
                return 1  # Returns 1 for successful batch delete
            except Exception as e:
                logger.error(f"Failed to delete memory vectors for {user_id}: {e}")
        return 0

    async def _delete_memories(self, user_id: str) -> int:
        """Delete user memories from MongoDB."""
        if self.db_client:
            try:
                result = await self.db_client.memories.delete_many({"user_id": user_id})
                return result.deleted_count
            except Exception as e:
                logger.error(f"Failed to delete memories for {user_id}: {e}")
        return 0

    async def _delete_profile(self, user_id: str) -> int:
        """Delete user profile."""
        if self.db_client:
            try:
                result = await self.db_client.users.delete_one({"user_id": user_id})
                return result.deleted_count
            except Exception as e:
                logger.error(f"Failed to delete profile for {user_id}: {e}")
        return 0

    async def _delete_preferences(self, user_id: str) -> int:
        """Delete user preferences."""
        if self.db_client:
            try:
                result = await self.db_client.preferences.delete_one({"user_id": user_id})
                return result.deleted_count
            except Exception as e:
                logger.error(f"Failed to delete preferences for {user_id}: {e}")
        return 0

    async def _delete_audit_logs(self, user_id: str) -> int:
        """Delete user audit logs."""
        if self.db_client:
            try:
                result = await self.db_client.audit_logs.delete_many({"user_id": user_id})
                return result.deleted_count
            except Exception as e:
                logger.error(f"Failed to delete audit logs for {user_id}: {e}")
        return 0

    async def _delete_provider_logs(self, user_id: str) -> int:
        """Delete provider usage logs."""
        if self.db_client:
            try:
                result = await self.db_client.provider_logs.delete_many({"user_id": user_id})
                return result.deleted_count
            except Exception as e:
                logger.error(f"Failed to delete provider logs for {user_id}: {e}")
        return 0

    def create_deletion_request(
        self,
        user_id: str,
        categories: Optional[List[str]] = None,
        confirm: bool = False,
    ) -> DataDeletionRequest:
        """Create a tracked deletion request."""
        request = DataDeletionRequest(
            user_id=user_id,
            requested_at=datetime.now(timezone.utc).isoformat(),
            categories=categories or [
                "messages", "sessions", "memories", "memories_vectors",
                "profile", "preferences", "audit_logs", "provider_logs"
            ],
            confirm=confirm,
        )
        request_id = f"delete_{user_id}_{int(datetime.now(timezone.utc).timestamp())}"
        self._deletion_requests[request_id] = request
        return request

    # =========================================================================
    # RECTIFICATION (GDPR Article 16)
    # =========================================================================

    async def rectify_user_data(
        self,
        user_id: str,
        corrections: Dict[str, Any],
    ) -> List[str]:
        """
        Rectify incorrect user data.
        
        Args:
            user_id: User identifier
            corrections: field -> new_value mappings
            
        Returns:
            List of fields updated
        """
        updated_fields = []
        
        if self.db_client:
            try:
                # Update profile
                profile_corrections = {k: v for k, v in corrections.items() 
                                    if k in ["name", "email", "timezone", "language"]}
                if profile_corrections:
                    await self.db_client.users.update_one(
                        {"user_id": user_id},
                        {"$set": profile_corrections}
                    )
                    updated_fields.extend(profile_corrections.keys())
                
                # Update preferences
                pref_corrections = {k: v for k, v in corrections.items()
                                  if k.startswith("pref_") or k in ["model", "theme", "notifications"]}
                if pref_corrections:
                    await self.db_client.preferences.update_one(
                        {"user_id": user_id},
                        {"$set": pref_corrections},
                        upsert=True
                    )
                    updated_fields.extend(pref_corrections.keys())
                
            except Exception as e:
                logger.error(f"Failed to rectify data for {user_id}: {e}")

        return updated_fields

    def create_rectification_request(
        self,
        user_id: str,
        corrections: Dict[str, Any],
    ) -> RectificationRequest:
        """Create a tracked rectification request."""
        request = RectificationRequest(
            user_id=user_id,
            requested_at=datetime.now(timezone.utc).isoformat(),
            corrections=corrections,
        )
        request_id = f"rectify_{user_id}_{int(datetime.now(timezone.utc).timestamp())}"
        self._rectification_requests[request_id] = request
        return request

    # =========================================================================
    # RESTRICT PROCESSING (GDPR Article 18)
    # =========================================================================

    async def restrict_processing(
        self,
        user_id: str,
        categories: List[str],
        reason: str,
    ) -> bool:
        """
        Restrict processing of user data.
        
        Args:
            user_id: User identifier
            categories: Data categories to restrict
            reason: Reason for restriction
            
        Returns:
            True if restriction applied
        """
        if self.db_client:
            try:
                # Mark user as restricted
                await self.db_client.users.update_one(
                    {"user_id": user_id},
                    {"$set": {
                        "processing_restricted": True,
                        "restricted_categories": categories,
                        "restriction_reason": reason,
                        "restricted_at": datetime.now(timezone.utc).isoformat(),
                    }}
                )
                return True
            except Exception as e:
                logger.error(f"Failed to restrict processing for {user_id}: {e}")
        return False

    def create_restriction_request(
        self,
        user_id: str,
        categories: List[str],
        reason: str,
    ) -> RestrictionRequest:
        """Create a tracked restriction request."""
        request = RestrictionRequest(
            user_id=user_id,
            requested_at=datetime.now(timezone.utc).isoformat(),
            categories=categories,
            reason=reason,
        )
        request_id = f"restrict_{user_id}_{int(datetime.now(timezone.utc).timestamp())}"
        self._restriction_requests[request_id] = request
        return request

    # =========================================================================
    # REQUEST TRACKING
    # =========================================================================

    def get_export_request(self, request_id: str) -> Optional[DataExportRequest]:
        return self._export_requests.get(request_id)

    def get_deletion_request(self, request_id: str) -> Optional[DataDeletionRequest]:
        return self._deletion_requests.get(request_id)

    def get_rectification_request(self, request_id: str) -> Optional[RectificationRequest]:
        return self._rectification_requests.get(request_id)

    def get_restriction_request(self, request_id: str) -> Optional[RestrictionRequest]:
        return self._restriction_requests.get(request_id)

    def list_user_requests(self, user_id: str) -> Dict[str, List]:
        """List all requests for a user."""
        return {
            "exports": [r for r in self._export_requests.values() if r.user_id == user_id],
            "deletions": [r for r in self._deletion_requests.values() if r.user_id == user_id],
            "rectifications": [r for r in self._rectification_requests.values() if r.user_id == user_id],
            "restrictions": [r for r in self._restriction_requests.values() if r.user_id == user_id],
        }


# Global instance
_user_data_controller: Optional[UserDataController] = None


def get_user_data_controller() -> UserDataController:
    global _user_data_controller
    if _user_data_controller is None:
        _user_data_controller = UserDataController()
    return _user_data_controller


__all__ = [
    "DataControlAction",
    "DataExportRequest",
    "DataDeletionRequest",
    "RectificationRequest",
    "RestrictionRequest",
    "UserDataController",
    "get_user_data_controller",
]