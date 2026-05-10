"""
Skill Base — Abstract Skill Definition

Defines what a skill is and the contract for skill execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import re


@dataclass
class SkillDefinition:
    """Complete definition of a skill loaded from YAML/JSON."""
    name: str
    description: str
    system_prompt: str
    priority: int = 5
    category: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    trigger_patterns: List[str] = field(default_factory=list)
    negative_patterns: List[str] = field(default_factory=list)
    allow_chain: bool = True
    cooldown_seconds: int = 0
    permissions: Dict[str, Any] = field(default_factory=dict)
    max_tokens: Optional[int] = None

    # Compiled regex patterns (built at load time)
    _compiled_triggers: List[re.Pattern] = field(
        default_factory=list, repr=False, compare=False
    )
    _compiled_negative: List[re.Pattern] = field(
        default_factory=list, repr=False, compare=False
    )

    def __post_init__(self):
        """Compile regex patterns at construction time."""
        self._compiled_triggers = []
        for pattern in self.trigger_patterns:
            try:
                self._compiled_triggers.append(re.compile(pattern, re.IGNORECASE))
            except re.error:
                # Invalid regex falls back to literal match
                self._compiled_triggers.append(
                    re.compile(re.escape(pattern), re.IGNORECASE)
                )

        self._compiled_negative = []
        for pattern in self.negative_patterns:
            try:
                self._compiled_negative.append(re.compile(pattern, re.IGNORECASE))
            except re.error:
                self._compiled_negative.append(
                    re.compile(re.escape(pattern), re.IGNORECASE)
                )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SkillDefinition:
        """Create a SkillDefinition from a dictionary (JSON/YAML)."""
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            system_prompt=data.get("system_prompt", ""),
            priority=data.get("priority", 5),
            category=data.get("category"),
            keywords=data.get("keywords", []),
            trigger_patterns=data.get("trigger_patterns", []),
            negative_patterns=data.get("negative_patterns", []),
            allow_chain=data.get("allow_chain", True),
            cooldown_seconds=data.get("cooldown_seconds", 0),
            permissions=data.get("permissions", {}),
            max_tokens=data.get("max_tokens"),
        )
