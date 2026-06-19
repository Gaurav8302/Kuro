"""Reflection Engine — main orchestrator for the full reflection pipeline.

Reads across memory stores, clusters related memories, generates insights,
validates them, and stores them. Follows MEMORY_REFLECTION.md Section 3.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from memory_v2.reflection.config import DEFAULT_REFLECTION_CONFIG, ReflectionConfig
from memory_v2.reflection.insight_manager import InsightManager
from memory_v2.reflection.insight_store import InsightStore
from memory_v2.reflection.insight_validator import InsightValidator
from memory_v2.reflection.scheduler import ReflectionScheduler
from memory_v2.reflection.types import (
    Insight,
    InsightStatus,
    InsightType,
    SupportingMemoryRef,
)

logger = logging.getLogger(__name__)


class ReflectionEngine:
    """Top-level orchestrator for the reflection pipeline.

    Pipeline (from MEMORY_REFLECTION.md):
      Gather → Cluster → Synthesize → Score → Validate → Store
    """

    def __init__(
        self,
        manager: Optional[InsightManager] = None,
        store: Optional[InsightStore] = None,
        validator: Optional[InsightValidator] = None,
        scheduler: Optional[ReflectionScheduler] = None,
        config: Optional[ReflectionConfig] = None,
        llm_fn: Optional[Callable] = None,
        memory_loader_fn: Optional[Callable] = None,
        embedding_fn: Optional[Callable] = None,
    ):
        self.config = config or DEFAULT_REFLECTION_CONFIG
        self.store = store or InsightStore(config=self.config)
        self.validator = validator or InsightValidator(config=self.config)
        self.manager = manager or InsightManager(
            store=self.store, validator=self.validator, config=self.config,
        )
        self.scheduler = scheduler or ReflectionScheduler(
            reflection_fn=self.run_reflection, config=self.config,
        )
        self.scheduler.set_reflection_fn(self.run_reflection)

        self._llm_fn = llm_fn
        self._memory_loader = memory_loader_fn
        self._embedding_fn = embedding_fn

    # ── Public API ──

    async def run_reflection(self, user_id: str, reason: str = "scheduled") -> List[Insight]:
        """Execute the full reflection pipeline.

        Returns list of new/updated insights.
        """
        logger.info("Reflection pipeline started (user=%s, reason=%s)", user_id, reason)

        memories = await self._gather_memories(user_id)
        if not memories or len(memories) < self.config.min_memories_for_reflection:
            logger.info(
                "Insufficient memories for reflection: %d (min %d)",
                len(memories) if memories else 0,
                self.config.min_memories_for_reflection,
            )
            return []

        existing_insights = self.store.get_active_insights(user_id)
        existing_pending = self.store.get_pending_insights(user_id)
        all_existing = existing_insights + existing_pending

        clusters = self._cluster_memories(memories)

        if not clusters:
            logger.info("No clusters found for user %s", user_id)
            clusters = await self._llm_theme_extraction(memories)
            if not clusters:
                return []

        new_insights: List[Insight] = []

        for cluster in clusters:
            if len(cluster) < self.config.min_cluster_size:
                continue

            candidate = await self._synthesize_insight(cluster)
            if candidate is None:
                continue

            candidate.confidence = self.manager.recompute_confidence(
                candidate, cluster, all_existing,
            )

            is_valid, reason_invalid = self.validator.validate(
                candidate, all_existing, cluster,
            )
            if not is_valid:
                logger.debug(
                    "Insight validation failed: %s (reason: %s)",
                    candidate.insight_text[:40], reason_invalid,
                )
                continue

            is_duplicate, merged = self.manager.merge_or_skip_duplicate(
                user_id, candidate, all_existing,
            )
            if is_duplicate and merged:
                new_insights.append(merged)
                continue

            conflicting = self.validator.detect_contradictions(
                candidate, existing_insights,
            )
            if conflicting:
                self.manager.handle_contradictions(
                    user_id, candidate, conflicting,
                )

            self.manager.insert_insight(user_id, candidate)
            new_insights.append(candidate)

        archived = self.manager.decay(user_id)
        if archived:
            logger.info("Archived %d insights by decay for user %s", archived, user_id)

        logger.info(
            "Reflection complete: %d new insights, %d existing (user=%s)",
            len(new_insights),
            len(existing_insights),
            user_id,
        )
        return new_insights

    async def reflect_on_demand(self, user_id: str) -> List[Insight]:
        """Force immediate full reflection."""
        return await self.run_reflection(user_id, reason="on_demand")

    async def reflect_on_new_memory(
        self, user_id: str, count: int = 1,
    ) -> Optional[List[Insight]]:
        """Called when new memories are added. May trigger reflection."""
        triggered = self.scheduler.record_memory_added(count)
        if triggered:
            return await self.run_reflection(user_id, reason="memory_threshold")
        return None

    async def reflect_on_session_end(self, user_id: str) -> Optional[List[Insight]]:
        """Called at session end."""
        if self.config.reflection_on_session_end:
            return await self.run_reflection(user_id, reason="session_end")
        return None

    def handle_correction(self, user_id: str, message: str) -> List[str]:
        """Handle user correction signal."""
        return self.manager.handle_correction(user_id, message)

    # ── Retrieval integration ──

    def should_retrieve_insights(self, query: str, context: Dict[str, Any]) -> bool:
        """Determine if insights should be injected for this query.

        Only inject for meta-cognitive or decision-making queries.
        """
        query_lower = query.lower().strip()

        meta_patterns = [
            "what do you know about me",
            "describe me",
            "what kind of person am i",
            "what have you learned about me",
            "tell me about yourself from my perspective",
            "what do you remember about me",
            "how would you describe me",
            "what are my",
        ]
        for pattern in meta_patterns:
            if pattern in query_lower:
                return True

        decision_patterns = [
            "what should i",
            "recommend",
            "should i use",
            "help me decide",
            "what do you suggest",
            "which one should",
        ]
        if context.get("is_decision_query"):
            return True
        for pattern in decision_patterns:
            if pattern in query_lower:
                return True

        return False

    def retrieve_relevant_insights(
        self, user_id: str, query: str, max_results: int = 5,
    ) -> List[Insight]:
        """Retrieve insights relevant to a query, ranked by relevance."""
        if not self.should_retrieve_insights(query, {}):
            return []

        insights = self.store.get_active_insights(user_id)
        if not insights:
            return []

        if not self._embedding_fn:
            scored = [
                (insight, self._keyword_relevance(query, insight.insight_text))
                for insight in insights
            ]
        else:
            query_embedding = self._embedding_fn(query)
            scored = []
            for insight in insights:
                insight_embedding = self._embedding_fn(insight.insight_text)
                relevance = self._cosine_similarity(query_embedding, insight_embedding)
                scored.append((insight, relevance))

        scored.sort(key=lambda x: x[1], reverse=True)

        filtered = [
            insight for insight, score in scored
            if score >= self.config.insight_relevance_threshold
        ]

        for insight in filtered[:max_results]:
            self.manager.reinforce(user_id, insight.id)

        return filtered[:max_results]

    # ── Memory integration helpers ──

    async def _gather_memories(self, user_id: str) -> List[Dict[str, Any]]:
        """Gather memories from all stores for reflection analysis."""
        if self._memory_loader:
            return await self._memory_loader(user_id=user_id)

        logger.warning("No memory_loader_fn configured; returning empty")
        return []

    # ── Clustering ──

    def _cluster_memories(
        self, memories: List[Dict[str, Any]]
    ) -> List[List[Dict[str, Any]]]:
        """Group memories by embedding similarity.

        Uses transitive closure: if A≈B and B≈C, then {A,B,C} is a cluster.
        """
        if not memories or len(memories) < self.config.min_cluster_size:
            return []

        if not self._embedding_fn:
            return self._keyword_cluster(memories)

        embeddings = []
        for mem in memories:
            content = mem.get("content") or mem.get("text", "")
            if not content:
                embeddings.append(None)
                continue
            try:
                emb = self._embedding_fn(content)
                embeddings.append(emb)
            except Exception:
                embeddings.append(None)

        threshold = self.config.cluster_similarity_threshold
        n = len(memories)
        adj: List[List[int]] = [[] for _ in range(n)]

        for i in range(n):
            if embeddings[i] is None:
                continue
            for j in range(i + 1, n):
                if embeddings[j] is None:
                    continue
                sim = self._cosine_similarity(embeddings[i], embeddings[j])
                if sim >= threshold:
                    adj[i].append(j)
                    adj[j].append(i)

        visited = [False] * n
        clusters: List[List[int]] = []

        for i in range(n):
            if not visited[i]:
                component = []
                stack = [i]
                while stack:
                    node = stack.pop()
                    if not visited[node]:
                        visited[node] = True
                        component.append(node)
                        for neighbor in adj[node]:
                            if not visited[neighbor]:
                                stack.append(neighbor)
                if len(component) >= self.config.min_cluster_size:
                    clusters.append(component)

        result = []
        for component in clusters:
            cluster_mems = [memories[idx] for idx in component]
            result.append(cluster_mems)

        return result

    def _keyword_cluster(
        self, memories: List[Dict[str, Any]]
    ) -> List[List[Dict[str, Any]]]:
        """Fallback clustering using keyword overlap when embeddings are unavailable."""
        if len(memories) < self.config.min_cluster_size:
            return []

        tokenized = []
        for mem in memories:
            content = (mem.get("content") or mem.get("text", "")).lower()
            tokens = set(w for w in content.split() if len(w) > 3)
            tokenized.append(tokens)

        n = len(memories)
        adj: List[List[int]] = [[] for _ in range(n)]
        threshold = 0.30

        for i in range(n):
            for j in range(i + 1, n):
                if not tokenized[i] or not tokenized[j]:
                    continue
                intersection = tokenized[i] & tokenized[j]
                union = tokenized[i] | tokenized[j]
                jaccard = len(intersection) / len(union)
                if jaccard >= threshold:
                    adj[i].append(j)
                    adj[j].append(i)

        visited = [False] * n
        clusters: List[List[int]] = []

        for i in range(n):
            if not visited[i]:
                component = []
                stack = [i]
                while stack:
                    node = stack.pop()
                    if not visited[node]:
                        visited[node] = True
                        component.append(node)
                        for neighbor in adj[node]:
                            if not visited[neighbor]:
                                stack.append(neighbor)
                if len(component) >= self.config.min_cluster_size:
                    clusters.append(component)

        result = []
        for component in clusters:
            cluster_mems = [memories[idx] for idx in component]
            result.append(cluster_mems)

        return result

    # ── LLM Synthesis ──

    async def _synthesize_insight(
        self, cluster: List[Dict[str, Any]]
    ) -> Optional[Insight]:
        """Generate an insight candidate from a memory cluster using LLM."""
        if not self._llm_fn:
            return self._rule_based_synthesis(cluster)

        memory_list = "\n".join(
            f"- [{m.get('type', 'unknown')}] {m.get('content') or m.get('text', '')}"
            for m in cluster
        )

        prompt = (
            "You are analyzing a set of memories about a user to generate higher-level insights. "
            "An insight is a hypothesis that explains MULTIPLE observations — it should be "
            "something not directly stated in any single memory, but evident from the pattern.\n\n"
            f"Cluster of {len(cluster)} memories:\n{memory_list}\n\n"
            "Generate an insight using this format:\n"
            "{\n"
            '  "statement": "Concise single-sentence insight about the user",\n'
            '  "type": "trait|pattern|contradiction|summary",\n'
            '  "reasoning": "Brief explanation of how this follows from the memories",\n'
            '  "naming": "Short label (2-4 words)"\n'
            "}\n\n"
            "RULES:\n"
            "- Do NOT repeat any single memory verbatim as the insight\n"
            "- Do NOT generate insights from only 1-2 memories\n"
            "- If memories contradict each other, set type to 'contradiction'\n"
            "- If memories don't form a clear pattern, return null\n"
            "- Output ONLY valid JSON, no other text"
        )

        try:
            result = await self._llm_fn(prompt)
            parsed = self._parse_synthesis(result)
            if parsed is None:
                return None

            categories = list(set(
                m.get("type") or m.get("metadata", {}).get("type", "unknown")
                for m in cluster
            ))

            evidence = [
                SupportingMemoryRef(
                    id=m.get("id") or m.get("metadata", {}).get("id", ""),
                    type=m.get("type") or m.get("metadata", {}).get("type", "unknown"),
                    content=m.get("content") or m.get("text", ""),
                    relevance=0.0,
                )
                for m in cluster
            ]

            return Insight.create(
                insight_text=parsed["statement"],
                insight_type=InsightType(parsed.get("type", "trait")),
                supporting_memories=evidence,
                source_categories=categories,
                reasoning=parsed.get("reasoning", ""),
                summary_label=parsed.get("naming", ""),
            )
        except Exception as e:
            logger.error("LLM synthesis failed: %s", e)
            return None

    def _rule_based_synthesis(
        self, cluster: List[Dict[str, Any]]
    ) -> Optional[Insight]:
        """Rule-based fallback when no LLM is available.

        Extracts a theme by finding the most common meaningful words across the cluster.
        """
        if len(cluster) < self.config.min_cluster_size:
            return None

        word_freq: Dict[str, int] = {}
        stopwords = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "shall", "can", "to", "of", "in", "for",
            "on", "with", "at", "by", "from", "and", "or", "but", "not", "so",
            "if", "than", "that", "this", "it", "its", "i", "me", "my", "you",
            "your", "we", "our", "they", "them", "their", "what", "which",
            "who", "how", "user", "uses", "using", "used",
        }

        for mem in cluster:
            content = (mem.get("content") or mem.get("text", "")).lower()
            words = content.split()
            for w in words:
                w = w.strip(".,!?;:'\"()[]")
                if w and len(w) > 3 and w not in stopwords:
                    word_freq[w] = word_freq.get(w, 0) + 1

        if not word_freq:
            return None

        significant = sorted(word_freq.items(), key=lambda x: -x[1])
        top_words = [w for w, c in significant[:5] if c >= max(2, len(cluster) // 2)]

        if len(top_words) < 2:
            return None

        categories = list(set(
            m.get("type") or m.get("metadata", {}).get("type", "unknown")
            for m in cluster
        ))

        insight_text = f"User frequently engages with topics related to {', '.join(top_words[:3])}"
        summary_label = "_".join(top_words[:2])

        evidence = [
            SupportingMemoryRef(
                id=m.get("id") or m.get("metadata", {}).get("id", str(i)),
                type=m.get("type") or m.get("metadata", {}).get("type", "unknown"),
                content=m.get("content") or m.get("text", ""),
                relevance=0.0,
            )
            for i, m in enumerate(cluster)
        ]

        return Insight.create(
            insight_text=insight_text,
            insight_type=InsightType.PATTERN,
            supporting_memories=evidence,
            source_categories=categories,
            reasoning=f"Rule-based theme extraction: common words = {significant[:3]}",
            summary_label=summary_label,
        )

    async def _llm_theme_extraction(
        self, memories: List[Dict[str, Any]]
    ) -> List[List[Dict[str, Any]]]:
        """Secondary clustering via LLM when embedding clustering yields nothing."""
        if not self._llm_fn or len(memories) < self.config.min_cluster_size:
            return []

        memory_list = "\n".join(
            f"- [{m.get('type', 'unknown')}] {m.get('content') or m.get('text', '')}"
            for m in memories
        )

        prompt = (
            "Given these memories about a user, identify any common themes or patterns. "
            "Only identify themes supported by at least 3 memories.\n\n"
            f"Memories:\n{memory_list}\n\n"
            "Return a JSON object mapping theme names to lists of memory indices (0-based):\n"
            '{"theme_name": [0, 2, 5]}'
        )

        try:
            result = await self._llm_fn(prompt)
            parsed = self._parse_llm_clusters(result)
            if not parsed:
                return []

            clusters = []
            for theme, indices in parsed.items():
                if len(indices) >= self.config.min_cluster_size:
                    cluster = [memories[i] for i in indices if i < len(memories)]
                    if cluster:
                        clusters.append(cluster)
            return clusters

        except Exception as e:
            logger.error("LLM theme extraction failed: %s", e)
            return []

    # ── Parsing helpers ──

    def _parse_synthesis(self, raw: str) -> Optional[Dict[str, str]]:
        """Parse LLM JSON output from synthesis prompt."""
        import json
        import re

        text = raw.strip()
        json_match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
        if json_match:
            text = json_match.group()

        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]

        text = text.strip()
        if text == "null" or not text:
            return None

        try:
            data = json.loads(text)
            if not isinstance(data, dict):
                return None
            statement = data.get("statement", "").strip()
            if not statement or len(statement) < 10:
                return None
            return {
                "statement": statement,
                "type": data.get("type", "trait"),
                "reasoning": data.get("reasoning", ""),
                "naming": data.get("naming", ""),
            }
        except (json.JSONDecodeError, ValueError):
            logger.warning("Failed to parse LLM synthesis output: %.100s", raw)
            return None

    def _parse_llm_clusters(self, raw: str) -> Dict[str, List[int]]:
        """Parse LLM JSON output from theme extraction prompt."""
        import json
        import re

        text = raw.strip()
        json_match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
        if json_match:
            text = json_match.group()

        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]

        try:
            data = json.loads(text)
            if not isinstance(data, dict):
                return {}
            result = {}
            for key, value in data.items():
                if isinstance(value, list):
                    indices = [int(i) for i in value if isinstance(i, (int, float))]
                    if len(indices) >= self.config.min_cluster_size:
                        result[key] = indices
            return result
        except (json.JSONDecodeError, ValueError, TypeError):
            logger.warning("Failed to parse LLM cluster output: %.100s", raw)
            return {}

    def _keyword_relevance(self, query: str, text: str) -> float:
        """Simple keyword relevance score when embeddings are unavailable."""
        query_words = set(w.lower() for w in query.split() if len(w) > 2)
        text_words = set(w.lower() for w in text.split() if len(w) > 2)
        if not query_words or not text_words:
            return 0.0
        overlap = len(query_words & text_words)
        return overlap / max(len(query_words), 1)

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
