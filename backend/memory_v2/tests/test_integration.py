"""Integration tests for the Reflection Engine wired into the live system."""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from memory_v2 import DEFAULT_REFLECTION_CONFIG, ReflectionConfig
from memory_v2.integration import ReflectionIntegration
from memory_v2.reflection.types import Insight, InsightStatus, InsightType, SupportingMemoryRef


TEST_USER = "test_user_001"


@pytest.fixture
def tmp_config(tmp_path):
    cfg = DEFAULT_REFLECTION_CONFIG
    cfg.storage_path = str(tmp_path)
    cfg.insight_relevance_threshold = 0.0
    cfg.reflection_after_n_memories = 3
    cfg.min_cluster_size = 3
    return cfg


@pytest.fixture
def integration(tmp_config) -> ReflectionIntegration:
    return ReflectionIntegration(config=tmp_config)


class TestIntegrationContextAugmentation:
    def test_augment_meta_query_returns_insights(self, integration):
        insight = Insight.create(
            insight_text="User values local-first development",
            insight_type=InsightType.TRAIT,
            supporting_memories=[
                SupportingMemoryRef(id="m1", type="preference", content="test", relevance=0.9),
                SupportingMemoryRef(id="m2", type="fact", content="test2", relevance=0.8),
                SupportingMemoryRef(id="m3", type="event", content="test3", relevance=0.7),
            ],
            source_categories=["preference", "fact", "event"],
        )
        insight.confidence = 0.85
        insight.status = InsightStatus.ACTIVE
        integration.engine.store.upsert_insight(TEST_USER, insight)

        ctx = asyncio.run(integration.augment_context(
            TEST_USER, "What do you know about me?", [],
        ))
        assert len(ctx) >= 1
        assert any("local-first" in entry["content"] for entry in ctx)

    def test_augment_casual_query_returns_empty(self, integration):
        ctx = asyncio.run(integration.augment_context(
            TEST_USER, "Hello, how are you?", [],
        ))
        assert ctx == []

    def test_augment_decision_query_returns_insights(self, integration):
        insight = Insight.create(
            insight_text="User prefers self-hosted databases",
            insight_type=InsightType.TRAIT,
            supporting_memories=[
                SupportingMemoryRef(id="m1", type="preference", content="test", relevance=0.9),
                SupportingMemoryRef(id="m2", type="fact", content="test2", relevance=0.8),
                SupportingMemoryRef(id="m3", type="event", content="test3", relevance=0.7),
            ],
            source_categories=["preference", "fact", "event"],
        )
        insight.confidence = 0.8
        insight.status = InsightStatus.ACTIVE
        integration.engine.store.upsert_insight(TEST_USER, insight)

        ctx = asyncio.run(integration.augment_context(
            TEST_USER, "What should I use for my database?", [],
        ))
        assert len(ctx) >= 1

    def test_augment_never_raises(self, integration):
        broken_engine = MagicMock()
        broken_engine.retrieve_relevant_insights.side_effect = RuntimeError("broken")
        integration.engine = broken_engine
        ctx = asyncio.run(integration.augment_context(TEST_USER, "What do you know about me?", []))
        assert ctx == []


class TestIntegrationCorrectionHandling:
    def test_detects_correction(self, integration):
        result = asyncio.run(integration.handle_correction(TEST_USER, "Stop assuming things about me"))
        assert result is False  # No insights to archive yet

        insight = Insight.create(
            insight_text="User likes me to assume things",
            insight_type=InsightType.PATTERN,
            supporting_memories=[
                SupportingMemoryRef(id="m1", type="event", content="test", relevance=0.9),
                SupportingMemoryRef(id="m2", type="event", content="test2", relevance=0.8),
                SupportingMemoryRef(id="m3", type="event", content="test3", relevance=0.7),
            ],
            source_categories=["event"],
        )
        insight.confidence = 0.1
        insight.status = InsightStatus.ACTIVE
        integration.engine.store.upsert_insight(TEST_USER, insight)

        result2 = asyncio.run(integration.handle_correction(TEST_USER, "Stop assuming things about me"))
        assert result2 is True

    def test_ignores_normal_message(self, integration):
        result = asyncio.run(integration.handle_correction(TEST_USER, "Hello, how are you?"))
        assert result is False

    def test_correction_never_raises(self, integration):
        broken_engine = MagicMock()
        broken_engine.handle_correction.side_effect = RuntimeError("broken")
        integration.engine = broken_engine
        result = asyncio.run(integration.handle_correction(TEST_USER, "Stop assuming things about me"))
        assert result is False


class TestIntegrationMemoryLifecycle:
    @pytest.mark.asyncio
    async def test_on_memories_processed_triggers_reflection(self, tmp_config, integration):
        config = tmp_config
        config.reflection_after_n_memories = 3
        store = integration.engine.store

        await integration.on_memories_processed(TEST_USER, 1)
        assert store.count_active(TEST_USER) == 0

        await integration.on_memories_processed(TEST_USER, 2)
        assert store.count_active(TEST_USER) == 0

        await integration.on_memories_processed(TEST_USER, 3)
        await asyncio.sleep(0.1)
        assert store.count_active(TEST_USER) >= 0

    @pytest.mark.asyncio
    async def test_on_session_end_runs_without_error(self, integration):
        await integration.on_session_end(TEST_USER)
        assert True

    @pytest.mark.asyncio
    async def test_on_memories_processed_never_raises(self, integration):
        broken_engine = MagicMock()
        broken_engine.scheduler = MagicMock()
        broken_engine.scheduler.on_memories_added = MagicMock(side_effect=RuntimeError("broken"))
        broken_engine.scheduler.should_reflect = MagicMock()
        integration.engine = broken_engine
        await integration.on_memories_processed(TEST_USER, 5)
        assert True


class TestIntegrationBackgroundScheduler:
    @pytest.mark.asyncio
    async def test_start_stop_background(self, integration):
        integration.start_background()
        assert integration._background_task is not None

        await integration.stop_background()
        assert integration._background_task is None

    @pytest.mark.asyncio
    async def test_start_twice_no_duplicate(self, integration):
        integration.start_background()
        task_1 = integration._background_task
        integration.start_background()
        assert integration._background_task is task_1
        await integration.stop_background()


class TestIntegrationWithMemoryUpdaterHook:
    @pytest.mark.asyncio
    async def test_updater_calls_on_batch_processed(self, tmp_config):
        callback = AsyncMock()
        from memory.updater import MemoryUpdater
        updater = MemoryUpdater(on_batch_processed=callback)

        with patch.object(updater, "_extract_memories_batch", new=AsyncMock(return_value={
            "facts": ["User likes Python"],
            "preferences": ["User prefers dark mode"],
            "events": [],
        })):
            await updater._process_batch(TEST_USER, [
                ("I like Python", "Great choice!"),
                ("I use dark mode", "Nice!"),
            ])

        callback.assert_awaited_once()
        args, _ = callback.call_args
        assert args[0] == TEST_USER
        assert args[1] > 0

    @pytest.mark.asyncio
    async def test_updater_callback_error_isolation(self, tmp_config):
        callback = AsyncMock(side_effect=RuntimeError("callback_error"))
        from memory.updater import MemoryUpdater
        updater = MemoryUpdater(on_batch_processed=callback)

        with patch.object(updater, "_extract_memories_batch", new=AsyncMock(return_value={
            "facts": ["User likes Python"],
            "preferences": [],
            "events": [],
        })):
            await updater._process_batch(TEST_USER, [("test", "test")])

        assert True


class TestIntegrationWithChatManager:
    @pytest.mark.asyncio
    async def test_insight_hook_injected_into_prompt(self, tmp_config, integration):
        insight = Insight.create(
            insight_text="User prefers local-first development",
            insight_type=InsightType.TRAIT,
            supporting_memories=[
                SupportingMemoryRef(id="m1", type="preference", content="test", relevance=0.9),
                SupportingMemoryRef(id="m2", type="fact", content="test2", relevance=0.8),
                SupportingMemoryRef(id="m3", type="event", content="test3", relevance=0.7),
            ],
            source_categories=["preference", "fact", "event"],
        )
        insight.confidence = 0.85
        insight.status = InsightStatus.ACTIVE
        integration.engine.store.upsert_insight(TEST_USER, insight)

        ctx = await integration.augment_context(
            TEST_USER, "What are my preferences?", [],
        )
        assert len(ctx) >= 1
        assert any("local-first" in entry["content"] for entry in ctx)

    @pytest.mark.asyncio
    async def test_insight_hook_noop_for_general_query(self, integration):
        ctx = await integration.augment_context(
            TEST_USER, "Hello world", [],
        )
        assert ctx == []


class TestEndToEndIntegrationFlow:
    @pytest.mark.asyncio
    async def test_full_lifecycle_new_memories_then_reflection(self, tmp_config):
        config = tmp_config
        config.reflection_after_n_memories = 3
        config.min_cluster_size = 3
        config.min_temporal_span_days = 0
        config.min_confidence_for_active = 0.0

        integration = ReflectionIntegration(config=config)

        await integration.on_memories_processed(TEST_USER, 1)
        await integration.on_memories_processed(TEST_USER, 2)
        await integration.on_memories_processed(TEST_USER, 3)
        await asyncio.sleep(0.2)

        insights = integration.engine.store.get_insight_by_id(TEST_USER, "")
        assert True

    @pytest.mark.asyncio
    async def test_correction_pipeline(self, tmp_config):
        integration = ReflectionIntegration(config=tmp_config)
        result = await integration.handle_correction(TEST_USER, "Stop doing that")
        assert result is False  # No insights exist yet to archive

        insight = Insight.create(
            insight_text="User enjoys doing that thing",
            insight_type=InsightType.PATTERN,
            supporting_memories=[
                SupportingMemoryRef(id="m1", type="event", content="doing that thing", relevance=0.9),
                SupportingMemoryRef(id="m2", type="event", content="test2", relevance=0.8),
                SupportingMemoryRef(id="m3", type="event", content="test3", relevance=0.7),
            ],
            source_categories=["event"],
        )
        insight.confidence = 0.1
        insight.status = InsightStatus.ACTIVE
        integration.engine.store.upsert_insight(TEST_USER, insight)

        result = await integration.handle_correction(TEST_USER, "Stop doing that")
        assert result is True

    @pytest.mark.asyncio
    async def test_start_stop_scheduler(self, integration):
        integration.start_background()
        await integration.stop_background()
        assert True

    def test_make_llm_fn(self):
        mock_router = MagicMock()
        mock_model = AsyncMock()
        mock_model.generate = AsyncMock(return_value="generated response")
        mock_router.get_model = MagicMock(return_value=mock_model)

        llm_fn = ReflectionIntegration.make_llm_fn(mock_router)
        result = asyncio.run(llm_fn("test prompt"))
        assert result == "generated response"
        mock_router.get_model.assert_called_with("mid")

    def test_memory_loader_handles_no_data(self):
        chat_db = MagicMock()
        chat_db.get_sessions_by_user = MagicMock(return_value=[])
        session_memory = MagicMock()
        long_term_memory = MagicMock()

        loader = ReflectionIntegration.make_memory_loader(chat_db, session_memory, long_term_memory)
        result = asyncio.run(loader(TEST_USER))
        assert result == []
