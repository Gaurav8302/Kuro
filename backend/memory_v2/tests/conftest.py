"""Test fixtures for reflection engine tests."""

import os
import sys
import tempfile
from typing import List

import pytest

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


@pytest.fixture
def temp_storage_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_memories():
    return [
        {
            "id": "mem_001",
            "type": "episodic",
            "content": "User built a local AI chatbot with Ollama",
            "confidence": 0.92,
            "timestamp": "2026-05-01T10:00:00Z",
            "created_at": "2026-05-01T10:00:00Z",
            "session_id": "sess_001",
            "embedding": [0.1, 0.2, 0.3],
        },
        {
            "id": "mem_002",
            "type": "preference",
            "content": "User prefers self-hosted over cloud",
            "confidence": 0.88,
            "timestamp": "2026-05-05T14:00:00Z",
            "created_at": "2026-05-05T14:00:00Z",
            "session_id": "sess_001",
            "embedding": [0.12, 0.22, 0.28],
        },
        {
            "id": "mem_003",
            "type": "semantic",
            "content": "User values data privacy",
            "confidence": 0.85,
            "timestamp": "2026-05-10T09:00:00Z",
            "created_at": "2026-05-10T09:00:00Z",
            "session_id": "sess_002",
            "embedding": [0.15, 0.18, 0.32],
        },
        {
            "id": "mem_004",
            "type": "episodic",
            "content": "User runs everything on local hardware",
            "confidence": 0.90,
            "timestamp": "2026-05-15T16:00:00Z",
            "created_at": "2026-05-15T16:00:00Z",
            "session_id": "sess_002",
            "embedding": [0.11, 0.21, 0.31],
        },
        {
            "id": "mem_005",
            "type": "preference",
            "content": "User rejected cloud recommendation",
            "confidence": 0.75,
            "timestamp": "2026-05-20T11:00:00Z",
            "created_at": "2026-05-20T11:00:00Z",
            "session_id": "sess_003",
            "embedding": [0.13, 0.19, 0.29],
        },
        {
            "id": "mem_006",
            "type": "episodic",
            "content": "User built a project called TabMind",
            "confidence": 0.95,
            "timestamp": "2026-04-01T10:00:00Z",
            "created_at": "2026-04-01T10:00:00Z",
            "session_id": "sess_004",
            "embedding": [0.5, 0.6, 0.1],
        },
        {
            "id": "mem_007",
            "type": "semantic",
            "content": "User studies computer science",
            "confidence": 0.90,
            "timestamp": "2026-05-01T10:00:00Z",
            "created_at": "2026-05-01T10:00:00Z",
            "session_id": "sess_004",
            "embedding": [0.48, 0.58, 0.15],
        },
    ]
