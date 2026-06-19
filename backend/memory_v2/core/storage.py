"""Abstract storage backend with JSON implementation.

Supports the StorageBackend interface from MEMORY_ARCHITECTURE_V2.md.
JsonStorage is the default; SqliteStorage can be swapped in later.
"""

from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    @abstractmethod
    def load(self, filepath: str) -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    def save(self, filepath: str, data: Dict[str, Any]) -> None:
        ...

    @abstractmethod
    def transaction(self, filepath: str, update_fn) -> Dict[str, Any]:
        ...


class JsonStorage(StorageBackend):
    def __init__(self, base_path: str = "backend/memory_v2/data"):
        self.base_path = base_path
        os.makedirs(self.base_path, exist_ok=True)

    def _resolve_path(self, filepath: str) -> str:
        if not os.path.isabs(filepath):
            return os.path.join(self.base_path, filepath)
        return filepath

    def load(self, filepath: str) -> Optional[Dict[str, Any]]:
        path = self._resolve_path(filepath)
        try:
            if not os.path.exists(path):
                return None
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error("JsonStorage.load failed for %s: %s", path, e)
            return None
        except Exception as e:
            logger.error("JsonStorage.load unexpected error for %s: %s", path, e)
            return None

    def save(self, filepath: str, data: Dict[str, Any]) -> None:
        path = self._resolve_path(filepath)
        try:
            tmp_path = path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, path)
        except Exception as e:
            logger.error("JsonStorage.save failed for %s: %s", path, e)
            raise

    def transaction(self, filepath: str, update_fn) -> Dict[str, Any]:
        data = self.load(filepath) or {}
        updated = update_fn(data)
        self.save(filepath, updated)
        return updated

    def load_user_data(self, filepath: str, user_id: str) -> Optional[Dict[str, Any]]:
        path = self._resolve_path(filepath)
        data = self.load(filepath)
        if data is None:
            return None
        if data.get("user_id") != user_id:
            logger.warning(
                "User ID mismatch: file has %s, requested %s",
                data.get("user_id"), user_id,
            )
            return None
        return data

    def init_user_file(self, filepath: str, user_id: str) -> Dict[str, Any]:
        path = self._resolve_path(filepath)
        if os.path.exists(path):
            existing = self.load(filepath)
            if existing:
                return existing
        data = {"version": 1, "user_id": user_id, "insights": [], "global": {}}
        self.save(filepath, data)
        return data
