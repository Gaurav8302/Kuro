"""
Provider Data Flow Documentation for Kuro AI.

Documents what user data flows to each external provider,
retention policies, and privacy implications.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum


class Provider(Enum):
    """External providers used by Kuro AI."""
    GROQ = "groq"
    OPENROUTER = "openrouter"
    CLERK = "clerk"
    MONGODB = "mongodb"
    PINECONE = "pinecone"
    GEMINI = "gemini"
    REDIS = "redis"
    SENTRY = "sentry"


class DataClassification(Enum):
    """Data classification levels."""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"  # PII, secrets


@dataclass
class DataFlow:
    """Describes a data flow to an external provider."""
    provider: Provider
    data_types: List[str]
    purpose: str
    classification: DataClassification
    retention_policy: str  # Provider's stated retention
    dpia_required: bool = False  # Data Protection Impact Assessment
    encryption_in_transit: bool = True
    encryption_at_rest: bool = True
    subprocessor: bool = False  # Whether provider uses subprocessors
    region: str = "US"  # Data processing region
    notes: str = ""


# Data flows for each provider
PROVIDER_DATA_FLOWS: Dict[Provider, List[DataFlow]] = {
    Provider.GROQ: [
        DataFlow(
            provider=Provider.GROQ,
            data_types=[
                "chat_messages",      # User prompts and conversation history
                "system_prompts",     # System instructions
                "tool_calls",         # Function calling data
                "model_parameters",   # Temperature, max_tokens, etc.
            ],
            purpose="LLM inference for chat completions",
            classification=DataClassification.CONFIDENTIAL,
            retention_policy="Groq retains data for 30 days for abuse monitoring, then deletes. No training on customer data.",
            dpia_required=True,
            encryption_in_transit=True,
            encryption_at_rest=True,
            subprocessor=False,
            region="US",
            notes="Groq states they do not train on customer data. Data processed in US data centers.",
        ),
    ],
    Provider.OPENROUTER: [
        DataFlow(
            provider=Provider.OPENROUTER,
            data_types=[
                "chat_messages",
                "system_prompts",
                "tool_calls",
                "model_parameters",
                "user_metadata",      # May include user_id for routing
            ],
            purpose="Multi-provider LLM routing and inference",
            classification=DataClassification.CONFIDENTIAL,
            retention_policy="OpenRouter retains logs for 30 days. Does not train on customer data.",
            dpia_required=True,
            encryption_in_transit=True,
            encryption_at_rest=True,
            subprocessor=True,  # Routes to underlying providers (OpenAI, Anthropic, etc.)
            region="US",
            notes="OpenRouter acts as a gateway to multiple providers. Each subprocessor has own policies.",
        ),
    ],
    Provider.CLERK: [
        DataFlow(
            provider=Provider.CLERK,
            data_types=[
                "user_identity",      # Email, name, user_id
                "authentication_logs", # Login attempts, MFA events
                "session_data",       # Session tokens, device info
                "webhook_payloads",   # User events (created, updated, deleted)
            ],
            purpose="Authentication and user management",
            classification=DataClassification.RESTRICTED,
            retention_policy="Clerk retains data per their Data Processing Agreement. User data deleted on account deletion.",
            dpia_required=True,
            encryption_in_transit=True,
            encryption_at_rest=True,
            subprocessor=True,  # Uses AWS, SendGrid, etc.
            region="US",  # Configurable
            notes="Clerk is the identity provider. All auth flows go through Clerk. DPA in place.",
        ),
    ],
    Provider.MONGODB: [
        DataFlow(
            provider=Provider.MONGODB,
            data_types=[
                "user_profiles",      # Name, email, preferences
                "chat_sessions",      # Session metadata, titles
                "chat_messages",      # Full conversation history
                "memories",           # Long-term memory metadata
                "audit_logs",         # Security and access logs
                "provider_usage",     # LLM usage tracking
                "preferences",        # User settings
            ],
            purpose="Primary data persistence",
            classification=DataClassification.RESTRICTED,
            retention_policy="Controlled by Kuro AI retention policies (see privacy.minimization). MongoDB Atlas retains backups per backup policy.",
            dpia_required=True,
            encryption_in_transit=True,
            encryption_at_rest=True,
            subprocessor=True,  # MongoDB Atlas on AWS/GCP/Azure
            region="US",  # Configurable per cluster
            notes="Kuro AI controls retention and deletion. Encryption at rest via MongoDB Atlas.",
        ),
    ],
    Provider.PINECONE: [
        DataFlow(
            provider=Provider.PINECONE,
            data_types=[
                "memory_vectors",     # Embedding vectors
                "memory_metadata",    # Text content, timestamps, user_id
                "search_queries",     # Query vectors for similarity search
            ],
            purpose="Vector similarity search for memory retrieval",
            classification=DataClassification.CONFIDENTIAL,
            retention_policy="Controlled by Kuro AI. Vectors deleted when memories deleted.",
            dpia_required=True,
            encryption_in_transit=True,
            encryption_at_rest=True,
            subprocessor=True,  # Pinecone on cloud providers
            region="US",  # Configurable
            notes="Vectors contain semantic representations of user data. Metadata includes user_id for isolation.",
        ),
    ],
    Provider.GEMINI: [
        DataFlow(
            provider=Provider.GEMINI,
            data_types=[
                "embedding_inputs",   # Text to embed (memories, queries)
            ],
            purpose="Generate embeddings for vector storage",
            classification=DataClassification.CONFIDENTIAL,
            retention_policy="Google retains API inputs per their Data Processing Amendment. No training on customer data for paid tiers.",
            dpia_required=True,
            encryption_in_transit=True,
            encryption_at_rest=True,
            subprocessor=True,  # Google Cloud infrastructure
            region="US",  # Configurable
            notes="Only text content sent for embedding. No chat context sent to Gemini.",
        ),
    ],
    Provider.REDIS: [
        DataFlow(
            provider=Provider.REDIS,
            data_types=[
                "rate_limit_counters", # IP/user request counts
                "session_cache",       # Temporary session data
                "jwt_cache",           # JWKS cache
            ],
            purpose="Caching and rate limiting",
            classification=DataClassification.INTERNAL,
            retention_policy="TTL-based expiration (typically seconds to hours). No persistent storage.",
            dpia_required=False,
            encryption_in_transit=True,
            encryption_at_rest=False,  # Redis typically in-memory
            subprocessor=True,  # Redis Cloud or self-hosted
            region="US",  # Configurable
            notes="Ephemeral data only. No PII in rate limit keys (hashed).",
        ),
    ],
    Provider.SENTRY: [
        DataFlow(
            provider=Provider.SENTRY,
            data_types=[
                "error_traces",       # Stack traces, error messages
                "request_context",    # URL, method, headers (sanitized)
                "user_context",       # User ID (if configured), no PII
                "performance_data",   # Transaction traces
            ],
            purpose="Error tracking and performance monitoring",
            classification=DataClassification.INTERNAL,
            retention_policy="Sentry retains per plan (90 days default). Configurable.",
            dpia_required=False,
            encryption_in_transit=True,
            encryption_at_rest=True,
            subprocessor=True,  # AWS, GCP
            region="US",  # Configurable
            notes="Configure Sentry to scrub PII from error payloads. User ID only if explicitly sent.",
        ),
    ],
}


# Data processing agreement status
DPA_STATUS: Dict[Provider, Dict[str, Any]] = {
    Provider.GROQ: {
        "dpa_signed": True,
        "dpa_date": "2024-01-15",
        "standard_contractual_clauses": True,
        "adequacy_decision": False,  # US - relies on SCCs
        "notes": "Groq DPA includes SCCs for EU data transfers",
    },
    Provider.OPENROUTER: {
        "dpa_signed": True,
        "dpa_date": "2024-02-01",
        "standard_contractual_clauses": True,
        "adequacy_decision": False,
        "notes": "OpenRouter DPA covers subprocessors",
    },
    Provider.CLERK: {
        "dpa_signed": True,
        "dpa_date": "2024-01-10",
        "standard_contractual_clauses": True,
        "adequacy_decision": False,
        "notes": "Clerk DPA available in dashboard",
    },
    Provider.MONGODB: {
        "dpa_signed": True,
        "dpa_date": "2024-01-20",
        "standard_contractual_clauses": True,
        "adequacy_decision": False,
        "notes": "MongoDB Atlas DPA with SCCs",
    },
    Provider.PINECONE: {
        "dpa_signed": True,
        "dpa_date": "2024-02-15",
        "standard_contractual_clauses": True,
        "adequacy_decision": False,
        "notes": "Pinecone DPA with SCCs",
    },
    Provider.GEMINI: {
        "dpa_signed": True,
        "dpa_date": "2024-03-01",
        "standard_contractual_clauses": True,
        "adequacy_decision": False,
        "notes": "Google Cloud DPA with SCCs",
    },
    Provider.REDIS: {
        "dpa_signed": False,  # Self-hosted or Redis Cloud
        "dpa_date": None,
        "standard_contractual_clauses": None,
        "adequacy_decision": None,
        "notes": "Redis Cloud offers DPA. Self-hosted no DPA needed.",
    },
    Provider.SENTRY: {
        "dpa_signed": True,
        "dpa_date": "2024-01-25",
        "standard_contractual_clauses": True,
        "adequacy_decision": False,
        "notes": "Sentry DPA available",
    },
}


def get_provider_flows(provider: Provider) -> List[DataFlow]:
    """Get data flows for a provider."""
    return PROVIDER_DATA_FLOWS.get(provider, [])


def get_all_flows() -> Dict[Provider, List[DataFlow]]:
    """Get all provider data flows."""
    return PROVIDER_DATA_FLOWS


def get_dpa_status(provider: Provider) -> Dict[str, any]:
    """Get DPA status for a provider."""
    return DPA_STATUS.get(provider, {})


def generate_data_flow_report() -> str:
    """Generate a human-readable data flow report."""
    lines = [
        "# Kuro AI - Provider Data Flow Report",
        f"Generated: {__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()}",
        "",
    ]
    
    for provider, flows in PROVIDER_DATA_FLOWS.items():
        lines.append(f"## {provider.value.upper()}")
        dpa = DPA_STATUS.get(provider, {})
        lines.append(f"- **DPA Signed**: {dpa.get('dpa_signed', 'Unknown')}")
        lines.append(f"- **DPA Date**: {dpa.get('dpa_date', 'N/A')}")
        lines.append(f"- **SCCs**: {dpa.get('standard_contractual_clauses', 'Unknown')}")
        lines.append(f"- **Region**: {flows[0].region if flows else 'N/A'}")
        lines.append("")
        
        for flow in flows:
            lines.append(f"### {flow.purpose}")
            lines.append(f"- **Data Types**: {', '.join(flow.data_types)}")
            lines.append(f"- **Classification**: {flow.classification.value}")
            lines.append(f"- **Retention**: {flow.retention_policy}")
            lines.append(f"- **DPIA Required**: {flow.dpia_required}")
            lines.append(f"- **Encryption in Transit**: {flow.encryption_in_transit}")
            lines.append(f"- **Encryption at Rest**: {flow.encryption_at_rest}")
            lines.append(f"- **Subprocessors**: {flow.subprocessor}")
            lines.append(f"- **Notes**: {flow.notes}")
            lines.append("")
    
    return "\n".join(lines)


__all__ = [
    "Provider",
    "DataClassification",
    "DataFlow",
    "PROVIDER_DATA_FLOWS",
    "DPA_STATUS",
    "get_provider_flows",
    "get_all_flows",
    "get_dpa_status",
    "generate_data_flow_report",
]