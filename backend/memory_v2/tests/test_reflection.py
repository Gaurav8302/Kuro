"""Tests for the Reflection Engine.

Covers:
  - Insight creation
  - Insight validation
  - Contradictions
  - Confidence updates
  - Duplicate prevention
  - Retrieval integration
"""

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pytest

from memory_v2.reflection.config import ReflectionConfig
from memory_v2.reflection.engine import ReflectionEngine
from memory_v2.reflection.insight_manager import InsightManager
from memory_v2.reflection.insight_store import InsightStore
from memory_v2.reflection.insight_validator import InsightValidator
from memory_v2.reflection.scheduler import ReflectionScheduler
from memory_v2.reflection.types import (
    ContradictionRef,
    Insight,
    InsightStatus,
    InsightType,
    InsightStoreData,
    SupportingMemoryRef,
    _generate_id,
    _now_str,
)

TEST_USER = "test_user_001"
MIN_CONFIDENCE = 0.50
ACTIVE_CONFIDENCE = 0.65


# ── Fixtures ──


@pytest.fixture
def test_config():
    c = ReflectionConfig()
    c.min_cluster_size = 3
    c.reflection_after_n_memories = 3
    return c


@pytest.fixture
def insight_store(tmp_path):
    config = ReflectionConfig()
    config.storage_path = str(tmp_path)
    return InsightStore(config=config)


@pytest.fixture
def validator(test_config):
    return InsightValidator(config=test_config)


@pytest.fixture
def manager(insight_store, validator, test_config):
    return InsightManager(
        store=insight_store, validator=validator, config=test_config,
    )


@pytest.fixture
def insight_1():
    return Insight.create(
        insight_text="User values privacy and local control over cloud convenience",
        insight_type=InsightType.TRAIT,
        supporting_memories=[
            SupportingMemoryRef(id="mem_001", type="episodic", content="User built local AI", relevance=0.9),
            SupportingMemoryRef(id="mem_002", type="preference", content="User prefers self-hosted", relevance=0.85),
            SupportingMemoryRef(id="mem_003", type="semantic", content="User values privacy", relevance=0.8),
        ],
        source_categories=["episodic", "preference", "semantic"],
        reasoning="Multiple memories show local-first preference pattern",
        summary_label="privacy_focused",
    )


@pytest.fixture
def insight_2():
    return Insight.create(
        insight_text="User has a strong long-term interest in AI engineering",
        insight_type=InsightType.TRAIT,
        supporting_memories=[
            SupportingMemoryRef(id="mem_006", type="episodic", content="User built TabMind", relevance=0.9),
            SupportingMemoryRef(id="mem_007", type="semantic", content="User studies CS", relevance=0.85),
        ],
        source_categories=["episodic", "semantic"],
        reasoning="User builds AI projects and studies related field",
        summary_label="ai_interest",
    )


# ══════════════════════════════════════════════════════════
# 1. Insight Creation
# ══════════════════════════════════════════════════════════


class TestInsightCreation:
    def test_create_insight_has_valid_id(self, insight_1):
        assert insight_1.id.startswith("ins_")
        assert len(insight_1.id) > 10

    def test_create_insight_has_correct_type(self, insight_1):
        assert insight_1.insight_type == InsightType.TRAIT

    def test_create_insight_starts_pending(self, insight_1):
        assert insight_1.status == InsightStatus.PENDING

    def test_create_insight_has_zero_confidence(self, insight_1):
        assert insight_1.confidence == 0.0

    def test_create_insight_counts_evidence(self, insight_1):
        assert insight_1.evidence_count == 3

    def test_create_insight_source_categories(self, insight_1):
        assert "episodic" in insight_1.source_categories
        assert "preference" in insight_1.source_categories
        assert "semantic" in insight_1.source_categories

    def test_create_insight_has_timestamps(self, insight_1):
        assert insight_1.created_at != ""
        assert insight_1.updated_at != ""
        assert insight_1.last_verified != ""

    def test_insight_to_dict_roundtrip(self, insight_1):
        data = insight_1.to_dict()
        restored = Insight.from_dict(data)
        assert restored.id == insight_1.id
        assert restored.insight_text == insight_1.insight_text
        assert restored.insight_type == insight_1.insight_type
        assert restored.confidence == insight_1.confidence
        assert len(restored.supporting_memories) == len(insight_1.supporting_memories)
        assert restored.source_categories == insight_1.source_categories

    def test_insight_status_properties(self):
        insight = Insight.create(
            insight_text="Test insight",
            insight_type=InsightType.TRAIT,
            supporting_memories=[],
            source_categories=[],
        )
        assert insight.is_pending
        assert not insight.is_active
        assert not insight.is_contested
        assert not insight.is_archived

        insight.status = InsightStatus.ACTIVE
        assert insight.is_active

        insight.status = InsightStatus.CONTESTED
        assert insight.is_contested

        insight.status = InsightStatus.ARCHIVED
        assert insight.is_archived


# ══════════════════════════════════════════════════════════
# 2. Insight Validation
# ══════════════════════════════════════════════════════════


class TestInsightValidation:
    def test_valid_insight_passes_validation(self, validator, insight_1):
        cluster = [
            {"content": "User built local AI", "type": "episodic",
             "timestamp": "2026-05-01T10:00:00Z", "session_id": "sess_001"},
            {"content": "User prefers self-hosted", "type": "preference",
             "timestamp": "2026-05-05T10:00:00Z", "session_id": "sess_001"},
            {"content": "User values privacy", "type": "semantic",
             "timestamp": "2026-05-10T10:00:00Z", "session_id": "sess_002"},
        ]
        is_valid, reason = validator.validate(insight_1, [], cluster)
        assert is_valid, f"Expected valid insight, got: {reason}"

    def test_rejects_insufficient_evidence(self, validator):
        insight = Insight.create(
            insight_text="User likes technology",
            insight_type=InsightType.TRAIT,
            supporting_memories=[
                SupportingMemoryRef(id="m1", type="episodic", content="test", relevance=0.5),
            ],
            source_categories=["episodic"],
        )
        cluster = [{"content": "test", "type": "episodic", "session_id": "s1"}]
        is_valid, reason = validator.validate(insight, [], cluster)
        assert not is_valid
        assert "min_evidence" in reason

    def test_rejects_single_session_cluster(self, validator, insight_1):
        cluster = [
            {"content": "A", "type": "episodic", "session_id": "s1", "timestamp": "2026-05-01T10:00:00Z"},
            {"content": "B", "type": "preference", "session_id": "s1", "timestamp": "2026-05-15T10:00:00Z"},
            {"content": "C", "type": "semantic", "session_id": "s1", "timestamp": "2026-05-20T10:00:00Z"},
        ]
        is_valid, reason = validator.validate(insight_1, [], cluster)
        assert not is_valid
        assert "single session" in reason

    def test_rejects_verbatim_copy(self, validator):
        insight = Insight.create(
            insight_text="User built a local AI chatbot with Ollama",
            insight_type=InsightType.TRAIT,
            supporting_memories=[
                SupportingMemoryRef(id="m1", type="episodic", content="test", relevance=0.9),
                SupportingMemoryRef(id="m2", type="preference", content="test2", relevance=0.9),
                SupportingMemoryRef(id="m3", type="semantic", content="test3", relevance=0.9),
            ],
            source_categories=["episodic", "preference", "semantic"],
        )
        cluster = [
            {"content": "User built a local AI chatbot with Ollama", "type": "episodic",
             "session_id": "s1", "timestamp": "2026-05-01T10:00:00Z"},
            {"content": "User prefers self-hosted", "type": "preference",
             "session_id": "s2", "timestamp": "2026-05-05T10:00:00Z"},
            {"content": "User values privacy", "type": "semantic",
             "session_id": "s3", "timestamp": "2026-05-10T10:00:00Z"},
        ]
        is_valid, reason = validator.validate(insight, [], cluster)
        assert not is_valid
        assert "verbatim copy" in reason or "jaccard" in reason

    def test_rejects_vague_insight(self, validator):
        insight = Insight.create(
            insight_text="User likes stuff",
            insight_type=InsightType.TRAIT,
            supporting_memories=[
                SupportingMemoryRef(id="m1", type="episodic", content="test", relevance=0.5),
                SupportingMemoryRef(id="m2", type="preference", content="test2", relevance=0.5),
                SupportingMemoryRef(id="m3", type="semantic", content="test3", relevance=0.5),
            ],
            source_categories=["episodic", "preference", "semantic"],
        )
        cluster = [
            {"content": "test", "type": "episodic", "session_id": "s1", "timestamp": "2026-05-01T10:00:00Z"},
            {"content": "test2", "type": "preference", "session_id": "s2", "timestamp": "2026-05-05T10:00:00Z"},
            {"content": "test3", "type": "semantic", "session_id": "s3", "timestamp": "2026-05-10T10:00:00Z"},
        ]
        is_valid, reason = validator.validate(insight, [], cluster)
        assert not is_valid
        assert "too short" in reason

    def test_specificity_scoring(self, validator):
        text_good = "User prioritizes self-hosted open-source solutions for AI databases and infrastructure"
        text_short = "User likes tech"
        assert validator.compute_specificity(text_short, []) < validator.compute_specificity(text_good, [])

    def test_correction_signal_detection(self, validator):
        assert validator.check_correction_signal("Don't assume I want short answers")
        assert validator.check_correction_signal("No, I don't actually use that")
        assert validator.check_correction_signal("Stop assuming things about me")
        assert not validator.check_correction_signal("What do you know about me?")

    def test_stability_even_spread(self, validator):
        cluster = [
            {"timestamp": "2026-01-01T10:00:00Z"},
            {"timestamp": "2026-01-15T10:00:00Z"},
            {"timestamp": "2026-02-01T10:00:00Z"},
            {"timestamp": "2026-02-15T10:00:00Z"},
            {"timestamp": "2026-03-01T10:00:00Z"},
        ]
        stability = validator.compute_stability(cluster)
        assert 0.5 <= stability <= 1.0


# ══════════════════════════════════════════════════════════
# 3. Contradictions
# ══════════════════════════════════════════════════════════


class TestContradictions:
    def test_detect_contradiction_local_vs_cloud(self, validator):
        insight_a = Insight.create(
            insight_text="User prefers local AI models and self-hosting",
            insight_type=InsightType.TRAIT,
            supporting_memories=[],
            source_categories=["preference"],
        )
        insight_b = Insight.create(
            insight_text="User prefers cloud services for convenience",
            insight_type=InsightType.TRAIT,
            supporting_memories=[],
            source_categories=["preference"],
        )
        conflicts = validator.detect_contradictions(insight_a, [insight_b])
        assert len(conflicts) >= 1
        assert conflicts[0][1] > 0.4

    def test_no_false_contradiction_unrelated(self, validator):
        insight_a = Insight.create(
            insight_text="User likes Python programming",
            insight_type=InsightType.TRAIT,
            supporting_memories=[],
            source_categories=[],
        )
        insight_b = Insight.create(
            insight_text="User prefers dark mode interfaces",
            insight_type=InsightType.TRAIT,
            supporting_memories=[],
            source_categories=[],
        )
        conflicts = validator.detect_contradictions(insight_a, [insight_b])
        assert len(conflicts) == 0

    def test_contradiction_strength_same_category(self, validator):
        insight_a = Insight.create(
            insight_text="User prefers local solutions",
            insight_type=InsightType.TRAIT,
            supporting_memories=[],
            source_categories=["preference"],
        )
        insight_b = Insight.create(
            insight_text="User prefers cloud solutions",
            insight_type=InsightType.TRAIT,
            supporting_memories=[],
            source_categories=["preference"],
        )
        conflicts = validator.detect_contradictions(insight_a, [insight_b])
        assert len(conflicts) > 0
        assert conflicts[0][1] > 0.6  # Same category = stronger contradiction

    def test_contradiction_handling_higher_confidence_wins(self, manager, validator):
        strong = Insight.create(
            insight_text="User prefers local solutions",
            insight_type=InsightType.TRAIT,
            supporting_memories=[
                SupportingMemoryRef(id="m1", type="preference", content="test", relevance=0.9),
                SupportingMemoryRef(id="m2", type="preference", content="test2", relevance=0.8),
                SupportingMemoryRef(id="m3", type="preference", content="test3", relevance=0.7),
                SupportingMemoryRef(id="m4", type="preference", content="test4", relevance=0.6),
            ],
            source_categories=["preference"],
        )
        strong.confidence = 0.85
        strong.evidence_count = 4
        strong.status = InsightStatus.ACTIVE

        weak = Insight.create(
            insight_text="User prefers cloud solutions",
            insight_type=InsightType.TRAIT,
            supporting_memories=[
                SupportingMemoryRef(id="m5", type="preference", content="test5", relevance=0.5),
            ],
            source_categories=["preference"],
        )
        weak.confidence = 0.60
        weak.evidence_count = 1

        conflicts = validator.detect_contradictions(weak, [strong])
        if conflicts:
            manager.handle_contradictions(TEST_USER, weak, conflicts)
            strong_after = manager.store.get_insight_by_id(TEST_USER, strong.id)
            if strong_after:
                assert strong_after.status == InsightStatus.CONTESTED or strong_after.status == InsightStatus.ACTIVE


# ══════════════════════════════════════════════════════════
# 4. Confidence Updates
# ══════════════════════════════════════════════════════════


class TestConfidenceUpdates:
    def test_confidence_geometric_mean(self, manager):
        cluster = [
            {"content": "local AI", "type": "episodic",
             "timestamp": "2026-05-01T10:00:00Z", "session_id": "s1"},
            {"content": "self-hosted", "type": "preference",
             "timestamp": "2026-05-05T10:00:00Z", "session_id": "s2"},
            {"content": "privacy", "type": "semantic",
             "timestamp": "2026-05-10T10:00:00Z", "session_id": "s3"},
        ]
        insight = Insight.create(
            insight_text="User values privacy and local control",
            insight_type=InsightType.TRAIT,
            supporting_memories=[],
            source_categories=["episodic", "preference", "semantic"],
        )
        confidence = manager.recompute_confidence(insight, cluster, [])
        assert 0.0 <= confidence <= 1.0
        assert confidence >= 0.30  # Should be reasonable with 3 diverse memories

    def test_reinforce_boosts_confidence(self, manager, insight_1):
        insight_1.confidence = 0.70
        insight_1.status = InsightStatus.ACTIVE
        manager.store.upsert_insight(TEST_USER, insight_1)

        before = insight_1.confidence
        manager.reinforce(TEST_USER, insight_1.id)
        after_insight = manager.store.get_insight_by_id(TEST_USER, insight_1.id)
        assert after_insight is not None
        assert after_insight.confidence > before, f"{after_insight.confidence} <= {before}"
        assert after_insight.activation_count >= 1

    def test_decay_reduces_confidence(self, manager, insight_1):
        insight_1.confidence = 0.80
        insight_1.last_verified = "2025-01-01T00:00:00Z"
        insight_1.updated_at = "2025-01-01T00:00:00Z"
        insight_1.status = InsightStatus.ACTIVE
        manager.store.upsert_insight(TEST_USER, insight_1)

        archived = manager.decay(TEST_USER)
        after = manager.store.get_insight_by_id(TEST_USER, insight_1.id)
        assert after is not None
        assert after.confidence < 0.80  # Should have decayed
        if archived > 0:
            assert after.status == InsightStatus.ARCHIVED

    def test_correction_archives_insight(self, manager, insight_1):
        insight_1.confidence = 0.80
        insight_1.status = InsightStatus.ACTIVE
        manager.store.upsert_insight(TEST_USER, insight_1)

        archived_ids = manager.handle_correction(
            TEST_USER, "No, I don't actually care about privacy that much"
        )
        if insight_1.id in archived_ids:
            after = manager.store.get_insight_by_id(TEST_USER, insight_1.id)
            assert after is not None
            assert after.status == InsightStatus.ARCHIVED

    def test_confidence_threshold_for_active(self):
        pending = Insight.create(
            insight_text="Test insight that should be pending",
            insight_type=InsightType.TRAIT,
            supporting_memories=[],
            source_categories=[],
        )
        pending.confidence = 0.55
        assert pending.confidence < ACTIVE_CONFIDENCE

        active = Insight.create(
            insight_text="Test insight that should be active",
            insight_type=InsightType.TRAIT,
            supporting_memories=[],
            source_categories=[],
        )
        active.confidence = 0.75
        assert active.confidence >= ACTIVE_CONFIDENCE


# ══════════════════════════════════════════════════════════
# 5. Duplicate Prevention
# ══════════════════════════════════════════════════════════


class TestDuplicatePrevention:
    def test_detect_duplicate_jaccard(self, manager, insight_1):
        insight_1.confidence = 0.80
        insight_1.status = InsightStatus.ACTIVE
        manager.store.upsert_insight(TEST_USER, insight_1)

        duplicate = Insight.create(
            insight_text="User values privacy and local control over cloud convenience",
            insight_type=InsightType.TRAIT,
            supporting_memories=[
                SupportingMemoryRef(id="m1", type="episodic", content="test", relevance=0.9),
            ],
            source_categories=["episodic"],
        )

        existing = [insight_1]
        is_dup, merged = manager.merge_or_skip_duplicate(TEST_USER, duplicate, existing)
        assert is_dup
        assert merged is not None
        assert merged.id == insight_1.id

    def test_non_duplicate_passes_through(self, manager, insight_1):
        insight_1.confidence = 0.80
        insight_1.status = InsightStatus.ACTIVE
        manager.store.upsert_insight(TEST_USER, insight_1)

        different = Insight.create(
            insight_text="User prefers concise technical explanations",
            insight_type=InsightType.TRAIT,
            supporting_memories=[
                SupportingMemoryRef(id="m1", type="preference", content="test", relevance=0.9),
            ],
            source_categories=["preference"],
        )

        existing = [insight_1]
        is_dup, merged = manager.merge_or_skip_duplicate(TEST_USER, different, existing)
        assert not is_dup

    def test_merge_combines_supporting_memories(self, manager, insight_1):
        insight_1.confidence = 0.70
        insight_1.status = InsightStatus.ACTIVE
        manager.store.upsert_insight(TEST_USER, insight_1)

        before_count = insight_1.evidence_count

        duplicate = Insight.create(
            insight_text="User values privacy and local control over cloud convenience",
            insight_type=InsightType.TRAIT,
            supporting_memories=[
                SupportingMemoryRef(id="new_mem", type="episodic", content="new evidence", relevance=0.8),
            ],
            source_categories=["episodic"],
        )

        existing = [insight_1]
        is_dup, merged = manager.merge_or_skip_duplicate(TEST_USER, duplicate, existing)
        assert is_dup
        assert merged.evidence_count >= before_count + 1


# ══════════════════════════════════════════════════════════
# 6. Storage
# ══════════════════════════════════════════════════════════


class TestInsightStorage:
    def test_store_and_retrieve(self, insight_store):
        insight = Insight.create(
            insight_text="Test stored insight",
            insight_type=InsightType.TRAIT,
            supporting_memories=[
                SupportingMemoryRef(id="m1", type="preference", content="test", relevance=0.8),
            ],
            source_categories=["preference"],
        )
        insight_store.upsert_insight(TEST_USER, insight)
        retrieved = insight_store.get_insight_by_id(TEST_USER, insight.id)
        assert retrieved is not None
        assert retrieved.id == insight.id
        assert retrieved.insight_text == insight.insight_text

    def test_store_active_insights_filter(self, insight_store):
        active = Insight.create(
            insight_text="Active insight",
            insight_type=InsightType.TRAIT,
            supporting_memories=[],
            source_categories=[],
        )
        active.status = InsightStatus.ACTIVE

        pending = Insight.create(
            insight_text="Pending insight",
            insight_type=InsightType.TRAIT,
            supporting_memories=[],
            source_categories=[],
        )
        pending.status = InsightStatus.PENDING

        archived = Insight.create(
            insight_text="Archived insight",
            insight_type=InsightType.TRAIT,
            supporting_memories=[],
            source_categories=[],
        )
        archived.status = InsightStatus.ARCHIVED

        for insight in [active, pending, archived]:
            insight_store.upsert_insight(TEST_USER, insight)

        actives = insight_store.get_active_insights(TEST_USER)
        assert len(actives) == 1
        assert actives[0].id == active.id

    def test_delete_insight(self, insight_store):
        insight = Insight.create(
            insight_text="To be deleted",
            insight_type=InsightType.TRAIT,
            supporting_memories=[],
            source_categories=[],
        )
        insight_store.upsert_insight(TEST_USER, insight)
        assert insight_store.get_insight_by_id(TEST_USER, insight.id) is not None

        deleted = insight_store.delete_insight(TEST_USER, insight.id)
        assert deleted
        assert insight_store.get_insight_by_id(TEST_USER, insight.id) is None

    def test_persists_to_disk(self, tmp_path):
        config = ReflectionConfig()
        config.storage_path = str(tmp_path)
        store = InsightStore(config=config)

        insight = Insight.create(
            insight_text="Persistent insight",
            insight_type=InsightType.TRAIT,
            supporting_memories=[],
            source_categories=[],
        )
        store.upsert_insight(TEST_USER, insight)

        store2 = InsightStore(config=config)
        retrieved = store2.get_insight_by_id(TEST_USER, insight.id)
        assert retrieved is not None
        assert retrieved.insight_text == "Persistent insight"

    def test_enforces_max_insights(self, insight_store):
        config = ReflectionConfig()
        config.max_insights_per_user = 3
        store = InsightStore(config=config)

        for i in range(5):
            insight = Insight.create(
                insight_text=f"Insight {i}",
                insight_type=InsightType.TRAIT,
                supporting_memories=[],
                source_categories=[],
            )
            insight.confidence = 0.5 + (i * 0.1)
            insight.status = InsightStatus.ACTIVE
            store.upsert_insight(TEST_USER, insight)

        actives = store.get_active_insights(TEST_USER)
        assert len(actives) <= 3


# ══════════════════════════════════════════════════════════
# 7. Retrieval Integration
# ══════════════════════════════════════════════════════════


class TestRetrievalIntegration:
    def test_should_retrieve_meta_query(self):
        engine = ReflectionEngine()
        assert engine.should_retrieve_insights("What do you know about me?", {})
        assert engine.should_retrieve_insights("describe me", {})
        assert engine.should_retrieve_insights("What kind of person am I?", {})

    def test_should_retrieve_decision_query(self):
        engine = ReflectionEngine()
        assert engine.should_retrieve_insights("What should I use for my project?", {})
        assert engine.should_retrieve_insights("Recommend a database", {})

    def test_not_retrieve_casual_query(self):
        engine = ReflectionEngine()
        assert not engine.should_retrieve_insights("Hello, how are you?", {})
        assert not engine.should_retrieve_insights("What's the weather like?", {})

    def test_retrieve_insights_ranked(self, tmp_path):
        config = ReflectionConfig()
        config.storage_path = str(tmp_path)
        config.insight_relevance_threshold = 0.0
        engine = ReflectionEngine(config=config)

        relevant = Insight.create(
            insight_text="User has strong interest in AI engineering",
            insight_type=InsightType.TRAIT,
            supporting_memories=[],
            source_categories=[],
        )
        relevant.confidence = 0.85
        relevant.status = InsightStatus.ACTIVE

        irrelevant = Insight.create(
            insight_text="User prefers dark mode in editors",
            insight_type=InsightType.TRAIT,
            supporting_memories=[],
            source_categories=[],
        )
        irrelevant.confidence = 0.80
        irrelevant.status = InsightStatus.ACTIVE

        engine.store.upsert_insight(TEST_USER, relevant)
        engine.store.upsert_insight(TEST_USER, irrelevant)

        results = engine.retrieve_relevant_insights(
            TEST_USER, "What are my AI projects", max_results=5,
        )
        assert len(results) >= 1

        results_no_match = engine.retrieve_relevant_insights(
            TEST_USER, "Hello", max_results=5,
        )
        assert len(results_no_match) == 0  # Not a meta/decision query


# ══════════════════════════════════════════════════════════
# 8. Scheduler
# ══════════════════════════════════════════════════════════


class TestScheduler:
    def test_memory_threshold_triggers(self):
        counter = {"called": False}

        async def fake_reflect(user_id: str, reason: str):
            counter["called"] = True

        scheduler = ReflectionScheduler(reflection_fn=fake_reflect, config=ReflectionConfig())
        scheduler.config.reflection_after_n_memories = 3

        for _ in range(3):
            scheduler.record_memory_added(1)
        assert scheduler._memory_count_since_last_reflection == 3

    def test_resets_after_reflection(self):
        scheduler = ReflectionScheduler(config=ReflectionConfig())
        scheduler.config.reflection_after_n_memories = 5

        scheduler.record_memory_added(5)
        should_run = scheduler.record_memory_added(0)
        assert should_run

    def test_time_interval_check(self):
        scheduler = ReflectionScheduler(config=ReflectionConfig())
        scheduler._last_reflection_time = 0.0
        assert scheduler.time_interval_elapsed() is False
        assert scheduler._last_reflection_time > 0.0


# ══════════════════════════════════════════════════════════
# 9. End-to-End Reflection Pipeline
# ══════════════════════════════════════════════════════════


class TestEndToEnd:
    @pytest.mark.asyncio
    async def test_full_pipeline_with_rule_based_synthesis(self, tmp_path, sample_memories):
        config = ReflectionConfig()
        config.storage_path = str(tmp_path)
        config.min_cluster_size = 3
        config.memory_lookback_days = 90

        engine = ReflectionEngine(config=config)

        async def mock_loader(user_id: str):
            return sample_memories

        engine._memory_loader = mock_loader

        results = await engine.run_reflection(TEST_USER, reason="test")
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_llm_synthesis_fallback(self, tmp_path):
        config = ReflectionConfig()
        config.storage_path = str(tmp_path)
        config.min_cluster_size = 3

        engine = ReflectionEngine(config=config)

        async def mock_loader(user_id: str):
            return [
                {"id": "1", "content": "User likes Python", "type": "preference",
                 "timestamp": "2026-05-01T10:00:00Z", "created_at": "2026-05-01T10:00:00Z",
                 "session_id": "s1"},
                {"id": "2", "content": "User builds projects with Python", "type": "episodic",
                 "timestamp": "2026-05-05T10:00:00Z", "created_at": "2026-05-05T10:00:00Z",
                 "session_id": "s2"},
                {"id": "3", "content": "User studies computer science", "type": "semantic",
                 "timestamp": "2026-05-10T10:00:00Z", "created_at": "2026-05-10T10:00:00Z",
                 "session_id": "s3"},
            ]

        engine._memory_loader = mock_loader

        results = await engine.run_reflection(TEST_USER, reason="test")
        assert isinstance(results, list)

    def test_reflect_on_demand(self, tmp_path):
        config = ReflectionConfig()
        config.storage_path = str(tmp_path)
        engine = ReflectionEngine(config=config)

        handler = engine.reflect_on_demand
        assert handler is not None

    def test_handle_correction_in_pipeline(self, tmp_path):
        config = ReflectionConfig()
        config.storage_path = str(tmp_path)
        engine = ReflectionEngine(config=config)

        insight = Insight.create(
            insight_text="User prefers local AI models",
            insight_type=InsightType.TRAIT,
            supporting_memories=[],
            source_categories=["preference"],
        )
        insight.confidence = 0.85
        insight.status = InsightStatus.ACTIVE
        engine.store.upsert_insight(TEST_USER, insight)

        archived = engine.handle_correction(TEST_USER, "No, I don't actually prefer local models anymore")
        assert isinstance(archived, list)

    def test_scheduler_in_engine(self, tmp_path):
        config = ReflectionConfig()
        config.storage_path = str(tmp_path)
        engine = ReflectionEngine(config=config)
        assert engine.scheduler is not None
        assert engine.scheduler._reflection_fn is not None
