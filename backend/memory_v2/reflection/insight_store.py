"""Insight storage — JSON persistence layer for insights.

Stores insights separately from memories in the file system.
Uses the JsonStorage backend from core.storage.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from memory_v2.core.storage import JsonStorage
from memory_v2.reflection.config import DEFAULT_REFLECTION_CONFIG
from memory_v2.reflection.types import Insight, InsightStatus, InsightStoreData

logger = logging.getLogger(__name__)


class InsightStore:
    def __init__(
        self,
        storage: Optional[JsonStorage] = None,
        config=None,
    ):
        self.config = config or DEFAULT_REFLECTION_CONFIG
        self.storage = storage or JsonStorage(base_path=self.config.storage_path)
        self._filename = self.config.insights_filename

    def _get_filepath(self, user_id: str) -> str:
        return f"{user_id}_{self._filename}"

    def load_all(self, user_id: str) -> InsightStoreData:
        filepath = self._get_filepath(user_id)
        raw = self.storage.load_user_data(filepath, user_id)
        if raw is None:
            raw = self.storage.init_user_file(filepath, user_id)
        return InsightStoreData.from_dict(raw)

    def save_all(self, data: InsightStoreData) -> None:
        if not data.user_id:
            logger.error("Cannot save insights without user_id")
            return
        filepath = self._get_filepath(data.user_id)
        self.storage.save(filepath, data.to_dict())

    def get_active_insights(self, user_id: str) -> List[Insight]:
        store_data = self.load_all(user_id)
        return [i for i in store_data.insights if i.status == "active"]

    def get_pending_insights(self, user_id: str) -> List[Insight]:
        store_data = self.load_all(user_id)
        return [i for i in store_data.insights if i.status == "pending"]

    def get_contested_insights(self, user_id: str) -> List[Insight]:
        store_data = self.load_all(user_id)
        return [i for i in store_data.insights if i.status == "contested"]

    def get_archived_insights(self, user_id: str) -> List[Insight]:
        store_data = self.load_all(user_id)
        return [i for i in store_data.insights if i.status == "archived"]

    def get_insight_by_id(self, user_id: str, insight_id: str) -> Optional[Insight]:
        store_data = self.load_all(user_id)
        for insight in store_data.insights:
            if insight.id == insight_id:
                return insight
        return None

    def upsert_insight(self, user_id: str, insight: Insight) -> None:
        store_data = self.load_all(user_id)
        for i, existing in enumerate(store_data.insights):
            if existing.id == insight.id:
                store_data.insights[i] = insight
                self.save_all(store_data)
                return
        store_data.insights.append(insight)
        self._enforce_max_insights(store_data)
        self.save_all(store_data)

    def delete_insight(self, user_id: str, insight_id: str) -> bool:
        store_data = self.load_all(user_id)
        before = len(store_data.insights)
        store_data.insights = [i for i in store_data.insights if i.id != insight_id]
        if len(store_data.insights) < before:
            self.save_all(store_data)
            return True
        return False

    def _enforce_max_insights(self, store_data: InsightStoreData) -> None:
        max_insights = self.config.max_insights_per_user
        active = [i for i in store_data.insights if i.status == "active"]
        if len(active) <= max_insights:
            return
        active.sort(key=lambda i: i.confidence)
        to_archive = active[: len(active) - max_insights]
        for insight in to_archive:
            insight.status = InsightStatus.ARCHIVED

    def count_active(self, user_id: str) -> int:
        return len(self.get_active_insights(user_id))

    def count_total(self, user_id: str) -> int:
        store_data = self.load_all(user_id)
        return len(store_data.insights)
