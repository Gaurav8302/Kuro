"""
Memory Compactor — Progressive Summarization

Implements progressive summarization for long-term memory management.
As memories age, they are condensed into higher-level summaries to
save storage and retrieval bandwidth while preserving key information.

Layers:
  L0: Raw memories (recent, high fidelity)
  L1: Daily summaries (1-7 days old)
  L2: Weekly summaries (1-4 weeks old)
  L3: Monthly summaries (1+ months old)
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class MemoryCompactor:
    """Progressive memory summarization engine."""

    # Age thresholds for each compression tier
    DAILY_THRESHOLD = timedelta(days=1)
    WEEKLY_THRESHOLD = timedelta(weeks=1)
    MONTHLY_THRESHOLD = timedelta(days=30)

    def __init__(self, llm_client=None):
        """
        Args:
            llm_client: An LLM client with an async .generate(prompt) method.
                       Used for summarization. If None, uses simple concatenation.
        """
        self.llm = llm_client

    async def compact(
        self,
        user_id: str,
        memories: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Compact a batch of memories using progressive summarization.

        Args:
            user_id: User whose memories to compact.
            memories: List of memory dicts with 'text', 'metadata', 'score'.

        Returns:
            List of compacted memories (fewer items, higher level summaries).
        """
        now = datetime.now(timezone.utc)

        # Bucket memories by age tier
        recent = []      # < 1 day — keep as-is
        daily = []        # 1-7 days — compress to daily summaries
        weekly = []       # 1-4 weeks — compress to weekly summaries
        monthly = []      # 1+ month — compress to monthly summaries

        for mem in memories:
            age = self._get_age(mem, now)
            if age < self.DAILY_THRESHOLD:
                recent.append(mem)
            elif age < self.WEEKLY_THRESHOLD:
                daily.append(mem)
            elif age < self.MONTHLY_THRESHOLD:
                weekly.append(mem)
            else:
                monthly.append(mem)

        result = list(recent)  # Keep recent memories intact

        # Summarize daily bucket
        if daily:
            summary = await self._summarize_group(daily, "daily")
            if summary:
                result.append(summary)

        # Summarize weekly bucket
        if weekly:
            summary = await self._summarize_group(weekly, "weekly")
            if summary:
                result.append(summary)

        # Summarize monthly bucket
        if monthly:
            summary = await self._summarize_group(monthly, "monthly")
            if summary:
                result.append(summary)

        logger.info(
            "Compacted %d memories → %d (recent=%d, daily=%d→1, weekly=%d→1, monthly=%d→1)",
            len(memories), len(result),
            len(recent), len(daily), len(weekly), len(monthly),
        )
        return result

    async def _summarize_group(
        self,
        memories: List[Dict[str, Any]],
        tier: str,
    ) -> Optional[Dict[str, Any]]:
        """Summarize a group of memories into a single summary memory."""
        if not memories:
            return None

        texts = [m.get("text", "") for m in memories if m.get("text")]
        if not texts:
            return None

        # Calculate aggregate importance
        importances = [
            float(m.get("metadata", {}).get("importance", 5))
            for m in memories
        ]
        avg_importance = sum(importances) / len(importances) if importances else 5.0

        if self.llm:
            # Use LLM for high-quality summarization
            summary_text = await self._llm_summarize(texts, tier)
        else:
            # Fallback: simple concatenation with dedup
            summary_text = self._simple_summarize(texts)

        return {
            "text": summary_text,
            "score": 0.5,
            "metadata": {
                "type": "summary",
                "tier": tier,
                "source_count": len(memories),
                "importance": min(avg_importance + 1, 10.0),
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        }

    async def _llm_summarize(self, texts: List[str], tier: str) -> str:
        """Use LLM to create a coherent summary."""
        combined = "\n- ".join(texts)
        prompt = (
            f"Summarize these {len(texts)} memory fragments into a concise {tier} summary.\n"
            "Keep all specific facts, names, dates, and preferences.\n"
            "Remove redundancy. Be concise.\n\n"
            f"Memories:\n- {combined}\n\n"
            "Summary:"
        )
        try:
            result = await self.llm.generate(prompt)
            return (result or "").strip()
        except Exception as e:
            logger.error("LLM summarization failed: %s", e)
            return self._simple_summarize(texts)

    @staticmethod
    def _simple_summarize(texts: List[str]) -> str:
        """Simple concatenation-based summary (fallback)."""
        # Deduplicate similar texts
        seen = set()
        unique = []
        for text in texts:
            key = text.lower().strip()[:100]
            if key not in seen:
                seen.add(key)
                unique.append(text.strip())
        return " | ".join(unique[:10])  # Cap at 10 items

    @staticmethod
    def _get_age(memory: Dict[str, Any], now: datetime) -> timedelta:
        """Get the age of a memory."""
        meta = memory.get("metadata", {})
        ts_str = meta.get("timestamp") or meta.get("created_at")
        if not ts_str:
            return timedelta(days=7)  # Default: assume 1 week old

        try:
            ts = datetime.fromisoformat(str(ts_str).replace("Z", "+00:00"))
            return now - ts
        except Exception:
            return timedelta(days=7)
