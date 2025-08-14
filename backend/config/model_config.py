"""Central model configuration for multi-source routing.

Defines:
- MODEL_SOURCES: OpenRouter vs Groq
- FALLBACK_CHAINS: ordered fallbacks per primary model
- RULE_KEYWORDS: rule-based intent -> model family mapping

Note: We keep this independent from model_registry.yml used by the legacy router,
so existing behavior remains intact. The new multi-model router consumes this file.
"""
from __future__ import annotations
from typing import Dict, List, Tuple

# Canonical model IDs used by the new router (symbolic, not provider-specific IDs)
CLAUDE_SONNET = "claude-3.5-sonnet"
CLAUDE_OPUS = "claude-3-opus"
CLAUDE_HAIKU = "claude-3-haiku"

GPT_4_TURBO = "gpt-4-turbo"
GPT_4O = "gpt-4o"
GPT_35_TURBO = "gpt-3.5-turbo"

MIXTRAL_8x7B_OR = "mixtral-8x7b-openrouter"
LLAMA3_70B_OR = "llama-3-70b-openrouter"
GEMINI_15_PRO = "gemini-1.5-pro"
GEMINI_15_FLASH = "gemini-1.5-flash"

# Groq-optimized
LLAMA3_8B_GROQ = "llama-3-8b-groq"
MIXTRAL_8x7B_GROQ = "mixtral-8x7b-groq"

# Source registry
MODEL_SOURCES: Dict[str, str] = {
    # OpenRouter
    CLAUDE_SONNET: "OpenRouter",
    CLAUDE_OPUS: "OpenRouter",
    CLAUDE_HAIKU: "OpenRouter",
    GPT_4_TURBO: "OpenRouter",
    GPT_4O: "OpenRouter",
    GPT_35_TURBO: "OpenRouter",
    MIXTRAL_8x7B_OR: "OpenRouter",
    LLAMA3_70B_OR: "OpenRouter",
    GEMINI_15_PRO: "OpenRouter",
    GEMINI_15_FLASH: "OpenRouter",
    # Groq
    LLAMA3_8B_GROQ: "Groq",
    MIXTRAL_8x7B_GROQ: "Groq",
}

# Fallback chains per requirement
FALLBACK_CHAINS: Dict[str, List[str]] = {
    CLAUDE_SONNET: [CLAUDE_SONNET, CLAUDE_OPUS, CLAUDE_HAIKU],
    GPT_4_TURBO: [GPT_4_TURBO, GPT_4O, GPT_35_TURBO],
    MIXTRAL_8x7B_OR: [MIXTRAL_8x7B_OR, MIXTRAL_8x7B_GROQ, LLAMA3_8B_GROQ],
    GEMINI_15_PRO: [GEMINI_15_PRO, GEMINI_15_FLASH, GPT_4O],
    LLAMA3_70B_OR: [LLAMA3_70B_OR, LLAMA3_8B_GROQ, MIXTRAL_8x7B_OR],
}

# Rule-based intent keyword mapping → preferred primary model
RULE_KEYWORDS: List[Tuple[str, List[str], str]] = [
    ("summarize", [r"\bsummariz(e|ing)\b", r"\bsummaris(e|ing)\b", r"\btldr\b", r"\bcondense\b"], CLAUDE_SONNET),
    ("translate", [r"\btranslate\b", r"\binto (english|spanish|french|german)\b"], GEMINI_15_PRO),
    ("code", [r"\bcode\b", r"\bdebug\b", r"```"], GPT_4_TURBO),
    ("math", [r"\b\d+\s*[\+\-\*\/\^]\s*\d+\b", r"\bsolve\b", r"\bmath\b"], GPT_4_TURBO),
    ("fast", [r"\bfast\b", r"real-time", r"realtime"], MIXTRAL_8x7B_GROQ),
    ("creative", [r"\bcreative\b", r"\bstory\b", r"\bpoem\b", r"\bimagine\b"], CLAUDE_OPUS),
    ("vision", [r"\bimage\b", r"\bvision\b", r"\bpicture\b"], GPT_4O),  # GPT-4o has vision
]


def get_model_source(model_id: str) -> str:
    return MODEL_SOURCES.get(model_id, "OpenRouter")


def get_fallback_chain(primary_model: str) -> List[str]:
    # default self-only chain
    return FALLBACK_CHAINS.get(primary_model, [primary_model])


def get_rule_keywords() -> List[Tuple[str, List[str], str]]:
    return RULE_KEYWORDS


__all__ = [
    "MODEL_SOURCES",
    "FALLBACK_CHAINS",
    "get_model_source",
    "get_fallback_chain",
    "get_rule_keywords",
    # ids
    "CLAUDE_SONNET",
    "CLAUDE_OPUS",
    "CLAUDE_HAIKU",
    "GPT_4_TURBO",
    "GPT_4O",
    "GPT_35_TURBO",
    "MIXTRAL_8x7B_OR",
    "MIXTRAL_8x7B_GROQ",
    "LLAMA3_70B_OR",
    "LLAMA3_8B_GROQ",
    "GEMINI_15_PRO",
    "GEMINI_15_FLASH",
]
