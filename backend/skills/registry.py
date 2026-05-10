"""
Skill Registry — Centralized Skill Management

Loads, stores, and manages skill definitions. Supports loading from
JSON files (backward compat with skills.json) and individual YAML files.
Provides hot-reload capability for development.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

from skills.base import SkillDefinition

logger = logging.getLogger(__name__)


class SkillRegistry:
    """Central registry for all skill definitions."""

    def __init__(self):
        self._skills: Dict[str, SkillDefinition] = {}
        self._load_order: List[str] = []

    @property
    def skills(self) -> List[SkillDefinition]:
        """Get all skills in load order."""
        return [self._skills[name] for name in self._load_order if name in self._skills]

    def get(self, name: str) -> Optional[SkillDefinition]:
        """Get a skill by name."""
        return self._skills.get(name)

    def register(self, skill: SkillDefinition) -> None:
        """Register a single skill."""
        if skill.name in self._skills:
            logger.warning("Overwriting skill: %s", skill.name)
        else:
            self._load_order.append(skill.name)
        self._skills[skill.name] = skill
        logger.debug("Registered skill: %s (priority=%d)", skill.name, skill.priority)

    def unregister(self, name: str) -> None:
        """Remove a skill from the registry."""
        self._skills.pop(name, None)
        if name in self._load_order:
            self._load_order.remove(name)

    def load_from_json(self, json_path: str) -> int:
        """Load skills from a JSON array file (backward compat with skills.json).

        Returns:
            Number of skills loaded.
        """
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, list):
                logger.error("skills.json must be a JSON array")
                return 0

            count = 0
            for item in data:
                try:
                    skill = SkillDefinition.from_dict(item)
                    self.register(skill)
                    count += 1
                except (KeyError, ValueError) as e:
                    logger.error("Failed to load skill from JSON: %s", e)

            logger.info("Loaded %d skills from %s", count, json_path)
            return count
        except Exception as e:
            logger.error("Failed to load skills from %s: %s", json_path, e)
            return 0

    def load_from_yaml_dir(self, dir_path: str) -> int:
        """Load skills from individual YAML files in a directory.

        Returns:
            Number of skills loaded.
        """
        try:
            import yaml
        except ImportError:
            logger.warning("PyYAML not installed; skipping YAML skill loading")
            return 0

        directory = Path(dir_path)
        if not directory.is_dir():
            logger.warning("Skill YAML directory not found: %s", dir_path)
            return 0

        count = 0
        for yaml_file in sorted(directory.glob("*.yaml")):
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if isinstance(data, dict):
                    skill = SkillDefinition.from_dict(data)
                    self.register(skill)
                    count += 1
            except Exception as e:
                logger.error("Failed to load skill from %s: %s", yaml_file, e)

        logger.info("Loaded %d skills from YAML dir %s", count, dir_path)
        return count

    def reload(self, json_path: Optional[str] = None, yaml_dir: Optional[str] = None):
        """Hot-reload all skills from their sources."""
        self._skills.clear()
        self._load_order.clear()
        loaded = 0
        if json_path:
            loaded += self.load_from_json(json_path)
        if yaml_dir:
            loaded += self.load_from_yaml_dir(yaml_dir)
        logger.info("Reloaded %d total skills", loaded)

    def __len__(self) -> int:
        return len(self._skills)

    def __contains__(self, name: str) -> bool:
        return name in self._skills


# Default registry instance
_default_registry: Optional[SkillRegistry] = None


def get_skill_registry() -> SkillRegistry:
    """Get or create the global skill registry."""
    global _default_registry
    if _default_registry is None:
        _default_registry = SkillRegistry()
        # Auto-load from skills.json if it exists
        skills_json = os.path.join(os.path.dirname(__file__), "skills.json")
        if os.path.exists(skills_json):
            _default_registry.load_from_json(skills_json)
        # Also load YAML definitions if directory exists
        yaml_dir = os.path.join(os.path.dirname(__file__), "definitions")
        if os.path.isdir(yaml_dir):
            _default_registry.load_from_yaml_dir(yaml_dir)
    return _default_registry
