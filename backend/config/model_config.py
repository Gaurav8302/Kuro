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
import logging

logger = logging.getLogger(__name__)

# --- begin normalization helpers ---
MODEL_NORMALIZATION: Dict[str, str] = {
    # canonical -> provider ID (expand as needed)
    "deepseek-r1": "deepseek/r1",
    "deepseek-r1-distill": "deepseek/r1-distill-qwen-14b",
    "deepseek-r1-distill-llama-70b": "deepseek-r1-distill-llama-70b",
    "llama-3.3-70b": "meta-llama/llama-3.3-70b-instruct",
    "llama-3.2-3b": "meta-llama/llama-3.2-3b-instruct",
    "llama-3.1-405b": "meta-llama/llama-3.1-405b-instruct",
    "qwen3-coder": "qwen/qwen-3-coder-480b-a35b",
    "qwen/qwen3-32b": "qwen/qwen3-32b",
    "gemini-2.0-flash": "google/gemini-2.0-flash-exp:free",
    "gemini-2.5-pro": "google/gemini-2.5-pro-exp:free",
    "mistral-nemo": "mistralai/mistral-nemo",
    "llama-3.1-8b-instant": "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile": "llama-3.3-70b-versatile",
    "gemma2-9b-it": "gemma2-9b-it",
    # legacy compatibility
    "claude-3.5-sonnet": "anthropic/claude-3.5-sonnet",
    "claude-3-opus": "anthropic/claude-3-opus",
    "claude-3-haiku": "anthropic/claude-3-haiku",
    "gpt-4-turbo": "openai/gpt-4-turbo",
    "gpt-4o": "openai/gpt-4o",
    "gpt-3.5-turbo": "openai/gpt-3.5-turbo",
    "mixtral-8x7b-openrouter": "mistralai/mixtral-8x7b-instruct",
    "llama-3-70b-openrouter": "meta-llama/llama-3-70b-instruct",
    "gemini-1.5-pro": "google/gemini-pro-1.5",
    "gemini-1.5-flash": "google/gemini-flash-1.5",
}

def normalize_model_id(model_id: str) -> str:
    """Normalize model ID to provider-ready format"""
    if not model_id:
        return model_id
    key = model_id.strip().lower()
    normalized = MODEL_NORMALIZATION.get(key, model_id)
    if normalized != model_id:
        logger.debug("Normalized model_id %s -> %s", model_id, normalized)
    return normalized
# --- end normalization helpers ---

# Canonical model IDs used by the new router (updated with best available models)

# === REASONING & COMPLEX TASKS ===
DEEPSEEK_R1 = "deepseek-r1"  # Best reasoning model (671B params, MIT license)
DEEPSEEK_R1_DISTILL = "deepseek-r1-distill"  # Fast reasoning (14B params, free)

# === HIGH-QUALITY CHAT MODELS ===
LLAMA_3_3_70B = "llama-3.3-70b"  # Excellent multilingual chat (70B)
LLAMA_3_1_405B = "llama-3.1-405b"  # Flagship model (405B params)

# === FAST & EFFICIENT ===
LLAMA_3_2_3B = "llama-3.2-3b"  # Ultra-fast small model (3B)
GEMINI_2_FLASH = "gemini-2.0-flash"  # Fast Google model with multimodal

# === CODING SPECIALIST ===
QWEN3_CODER = "qwen3-coder"  # Specialized coding model (480B params)

# === BALANCED PERFORMANCE ===
MISTRAL_NEMO = "mistral-nemo"  # 12B multilingual with 128k context
GEMINI_2_5_PRO = "gemini-2.5-pro"  # Google's advanced model

# === LEGACY PREMIUM (for fallbacks) ===
CLAUDE_SONNET = "claude-3.5-sonnet"
CLAUDE_OPUS = "claude-3-opus"
CLAUDE_HAIKU = "claude-3-haiku"
GPT_4_TURBO = "gpt-4-turbo"
GPT_4O = "gpt-4o"
GPT_35_TURBO = "gpt-3.5-turbo"

# Legacy compatibility
MIXTRAL_8x7B_OR = "mixtral-8x7b-openrouter"
LLAMA3_70B_OR = "llama-3-70b-openrouter"
GEMINI_15_PRO = "gemini-1.5-pro"
GEMINI_15_FLASH = "gemini-1.5-flash"

# Groq-optimized (using actual available Groq model names)
LLAMA3_8B_GROQ = "llama-3.1-8b-instant"  # Fast 8B model
LLAMA3_70B_GROQ = "llama-3.3-70b-versatile"  # 70B versatile model  
GEMMA2_9B = "gemma2-9b-it"  # Alternative fast model
DEEPSEEK_R1_GROQ = "deepseek-r1-distill-llama-70b"  # Reasoning model (Groq)
QWEN3_32B = "qwen/qwen3-32b"  # Alternative to Mixtral

# Compatibility aliases
MIXTRAL_8x7B_GROQ = QWEN3_32B  # Use Qwen as Mixtral alternative
LLAMA3_VERSATILE = LLAMA3_70B_GROQ  # Alias for 70B versatile

# Safe default model for fallbacks
SAFE_DEFAULT_MODEL = LLAMA3_8B_GROQ  # Fast, reliable Groq model as ultimate fallback

# Source registry (optimized for best available free models)
MODEL_SOURCES: Dict[str, str] = {
    # === OpenRouter (Free Tier - High Quality) ===
    # Reasoning specialists
    DEEPSEEK_R1: "OpenRouter",  # Best reasoning model
    DEEPSEEK_R1_DISTILL: "OpenRouter",  # Fast reasoning
    
    # Chat & general purpose  
    LLAMA_3_3_70B: "OpenRouter",  # Excellent multilingual
    LLAMA_3_1_405B: "OpenRouter",  # Flagship performance
    LLAMA_3_2_3B: "OpenRouter",  # Ultra-fast
    
    # Specialized
    QWEN3_CODER: "OpenRouter",  # Best for coding
    MISTRAL_NEMO: "OpenRouter",  # Balanced performance
    GEMINI_2_FLASH: "OpenRouter",  # Fast with multimodal
    GEMINI_2_5_PRO: "OpenRouter",  # Advanced Google model
    
    # === Groq (Fastest inference) ===
    LLAMA3_8B_GROQ: "Groq",  # llama-3.1-8b-instant
    LLAMA3_70B_GROQ: "Groq",  # llama-3.3-70b-versatile
    GEMMA2_9B: "Groq",  # gemma2-9b-it
    DEEPSEEK_R1_GROQ: "Groq",  # deepseek-r1-distill-llama-70b (Groq)
    QWEN3_32B: "Groq",  # qwen/qwen3-32b
    
    # === Legacy Premium (for paid fallbacks) ===
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
    
    # === Direct model name mappings ===
    # Groq models
    "llama-3.1-8b-instant": "Groq",
    "llama-3.3-70b-versatile": "Groq", 
    "gemma2-9b-it": "Groq",
    "deepseek-r1-distill-llama-70b": "Groq",
    "qwen/qwen3-32b": "Groq",
    
    # OpenRouter models (free tier)
    "deepseek/r1": "OpenRouter",
    "deepseek/r1-distill-qwen-14b": "OpenRouter",
    "meta-llama/llama-3.3-70b-instruct": "OpenRouter",
    "meta-llama/llama-3.2-3b-instruct": "OpenRouter",
    "meta-llama/llama-3.1-405b-instruct": "OpenRouter",
    "google/gemini-2.0-flash-exp:free": "OpenRouter",
    "google/gemini-2.5-pro-exp:free": "OpenRouter",
    "mistralai/mistral-nemo": "OpenRouter",
    "qwen/qwen-3-coder-480b-a35b": "OpenRouter",
}

# Fallback chains per requirement (optimized for free tier models)
FALLBACK_CHAINS: Dict[str, List[str]] = {
    # === OpenRouter Free Tier Models ===
    # Reasoning specialists
    DEEPSEEK_R1: [DEEPSEEK_R1, DEEPSEEK_R1_DISTILL, LLAMA_3_3_70B, LLAMA3_70B_GROQ],
    DEEPSEEK_R1_DISTILL: [DEEPSEEK_R1_DISTILL, DEEPSEEK_R1, LLAMA3_70B_GROQ, LLAMA_3_2_3B],
    
    # Chat & general purpose
    LLAMA_3_3_70B: [LLAMA_3_3_70B, LLAMA3_70B_GROQ, LLAMA_3_2_3B, LLAMA3_8B_GROQ],
    LLAMA_3_1_405B: [LLAMA_3_1_405B, LLAMA_3_3_70B, LLAMA3_70B_GROQ, DEEPSEEK_R1],
    LLAMA_3_2_3B: [LLAMA_3_2_3B, LLAMA3_8B_GROQ, GEMMA2_9B, MISTRAL_NEMO],
    
    # Specialized models
    QWEN3_CODER: [QWEN3_CODER, DEEPSEEK_R1, QWEN3_32B, LLAMA_3_3_70B],
    MISTRAL_NEMO: [MISTRAL_NEMO, LLAMA_3_2_3B, LLAMA3_8B_GROQ, GEMMA2_9B],
    GEMINI_2_FLASH: [GEMINI_2_FLASH, GEMINI_2_5_PRO, LLAMA_3_3_70B, LLAMA3_70B_GROQ],
    GEMINI_2_5_PRO: [GEMINI_2_5_PRO, GEMINI_2_FLASH, LLAMA_3_1_405B, DEEPSEEK_R1],
    
    # === Groq models (fastest) ===
    LLAMA3_8B_GROQ: [LLAMA3_8B_GROQ, GEMMA2_9B, LLAMA3_70B_GROQ, LLAMA_3_2_3B],
    LLAMA3_70B_GROQ: [LLAMA3_70B_GROQ, LLAMA_3_3_70B, LLAMA3_8B_GROQ, DEEPSEEK_R1],
    GEMMA2_9B: [GEMMA2_9B, LLAMA3_8B_GROQ, LLAMA_3_2_3B, MISTRAL_NEMO],
    DEEPSEEK_R1_GROQ: [DEEPSEEK_R1_GROQ, DEEPSEEK_R1, LLAMA3_70B_GROQ, QWEN3_32B],
    QWEN3_32B: [QWEN3_32B, QWEN3_CODER, LLAMA3_70B_GROQ, DEEPSEEK_R1],
    
    # === Legacy Premium Models (for paid fallbacks) ===
    CLAUDE_SONNET: [CLAUDE_SONNET, CLAUDE_OPUS, DEEPSEEK_R1, LLAMA_3_3_70B],
    CLAUDE_OPUS: [CLAUDE_OPUS, CLAUDE_SONNET, CLAUDE_HAIKU, DEEPSEEK_R1],
    CLAUDE_HAIKU: [CLAUDE_HAIKU, CLAUDE_SONNET, LLAMA_3_2_3B, LLAMA3_8B_GROQ],
    GPT_4_TURBO: [GPT_4_TURBO, GPT_4O, DEEPSEEK_R1, LLAMA_3_3_70B],
    GPT_4O: [GPT_4O, GPT_4_TURBO, GEMINI_2_5_PRO, LLAMA_3_1_405B],
    GPT_35_TURBO: [GPT_35_TURBO, LLAMA_3_2_3B, LLAMA3_8B_GROQ, MISTRAL_NEMO],
    MIXTRAL_8x7B_OR: [MIXTRAL_8x7B_OR, MISTRAL_NEMO, QWEN3_32B, LLAMA3_70B_GROQ],
    LLAMA3_70B_OR: [LLAMA3_70B_OR, LLAMA_3_3_70B, LLAMA3_70B_GROQ, LLAMA3_8B_GROQ],
    GEMINI_15_PRO: [GEMINI_15_PRO, GEMINI_2_5_PRO, GEMINI_2_FLASH, LLAMA_3_3_70B],
    GEMINI_15_FLASH: [GEMINI_15_FLASH, GEMINI_2_FLASH, LLAMA_3_2_3B, LLAMA3_8B_GROQ],
    
    # === Aliases ===
    MIXTRAL_8x7B_GROQ: [MISTRAL_NEMO, QWEN3_32B, LLAMA3_70B_GROQ, LLAMA3_8B_GROQ],
    LLAMA3_VERSATILE: [LLAMA3_70B_GROQ, LLAMA_3_3_70B, LLAMA3_8B_GROQ, GEMMA2_9B],
    
    # === Direct model name fallbacks ===
    # Groq models
    "llama-3.1-8b-instant": [LLAMA3_8B_GROQ, GEMMA2_9B, LLAMA_3_2_3B, MISTRAL_NEMO],
    "llama-3.3-70b-versatile": [LLAMA3_70B_GROQ, LLAMA_3_3_70B, LLAMA3_8B_GROQ, DEEPSEEK_R1],
    "gemma2-9b-it": [GEMMA2_9B, LLAMA3_8B_GROQ, LLAMA_3_2_3B, MISTRAL_NEMO],
    "deepseek-r1-distill-llama-70b": [DEEPSEEK_R1, DEEPSEEK_R1_DISTILL, LLAMA3_70B_GROQ, QWEN3_32B],
    "qwen/qwen3-32b": [QWEN3_32B, QWEN3_CODER, LLAMA3_70B_GROQ, DEEPSEEK_R1],
    
    # OpenRouter models (free tier)
    "deepseek/r1": [DEEPSEEK_R1, DEEPSEEK_R1_DISTILL, LLAMA_3_3_70B, LLAMA3_70B_GROQ],
    "deepseek/r1-distill-qwen-14b": [DEEPSEEK_R1_DISTILL, DEEPSEEK_R1, LLAMA3_70B_GROQ, LLAMA_3_2_3B],
    "meta-llama/llama-3.3-70b-instruct": [LLAMA_3_3_70B, LLAMA3_70B_GROQ, LLAMA_3_2_3B, LLAMA3_8B_GROQ],
    "meta-llama/llama-3.2-3b-instruct": [LLAMA_3_2_3B, LLAMA3_8B_GROQ, GEMMA2_9B, MISTRAL_NEMO],
    "meta-llama/llama-3.1-405b-instruct": [LLAMA_3_1_405B, LLAMA_3_3_70B, DEEPSEEK_R1, LLAMA3_70B_GROQ],
    "google/gemini-2.0-flash-exp:free": [GEMINI_2_FLASH, GEMINI_2_5_PRO, LLAMA_3_3_70B, LLAMA3_70B_GROQ],
    "google/gemini-2.5-pro-exp:free": [GEMINI_2_5_PRO, GEMINI_2_FLASH, LLAMA_3_1_405B, DEEPSEEK_R1],
    "mistralai/mistral-nemo": [MISTRAL_NEMO, LLAMA_3_2_3B, LLAMA3_8B_GROQ, GEMMA2_9B],
    "qwen/qwen-3-coder-480b-a35b": [QWEN3_CODER, DEEPSEEK_R1, QWEN3_32B, LLAMA_3_3_70B],
    
    # Legacy model IDs
    "llama3-70b-8192": [LLAMA3_70B_GROQ, LLAMA_3_3_70B, LLAMA3_8B_GROQ],
    "llama3-8b-8192": [LLAMA3_8B_GROQ, GEMMA2_9B, LLAMA_3_2_3B],
    "mixtral-8x7b-32768": [MISTRAL_NEMO, QWEN3_32B, LLAMA3_70B_GROQ],
}

# Intent-based routing configuration (best models per use case)
INTENT_MODEL_MAPPING: Dict[str, List[str]] = {
    "general": [
        LLAMA_3_3_70B,        # Primary: Excellent general chat
        DEEPSEEK_R1_DISTILL,  # Fallback: Good reasoning
        LLAMA3_70B_GROQ,      # Fast fallback
        LLAMA_3_2_3B,         # Ultra-fast fallback
    ],
    "coding": [
        QWEN3_CODER,          # Primary: Best coding model
        DEEPSEEK_R1,          # Fallback: Great reasoning
        LLAMA_3_3_70B,        # General fallback
        QWEN3_32B,            # Fast coding fallback
    ],
    "analysis": [
        DEEPSEEK_R1,          # Primary: Best reasoning
        LLAMA_3_1_405B,       # Fallback: Flagship model
        LLAMA_3_3_70B,        # General fallback
        DEEPSEEK_R1_DISTILL,  # Fast fallback
    ],
    "creative": [
        LLAMA_3_3_70B,        # Primary: Creative & versatile
        GEMINI_2_5_PRO,       # Fallback: Advanced creative
        MISTRAL_NEMO,         # Balanced fallback
        LLAMA_3_1_405B,       # Premium fallback
    ],
    "math": [
        DEEPSEEK_R1,          # Primary: Excellent reasoning
        LLAMA_3_1_405B,       # Fallback: Advanced math
        QWEN3_CODER,          # Code-based math
        GEMINI_2_5_PRO,       # Multi-step reasoning
    ],
    "quick": [
        LLAMA_3_2_3B,         # Primary: Ultra-fast
        LLAMA3_8B_GROQ,       # Fast Groq
        GEMMA2_9B,            # Fast Groq alternative
        MISTRAL_NEMO,         # Balanced speed
    ],
    "multimodal": [
        GEMINI_2_FLASH,       # Primary: Fast multimodal
        GEMINI_2_5_PRO,       # Advanced multimodal
        LLAMA_3_3_70B,        # Text fallback
        LLAMA_3_1_405B,       # Premium fallback
    ]
}

# Rule-based intent keyword mapping → preferred primary model (prioritizing best available models)
RULE_KEYWORDS: List[Tuple[str, List[str], str]] = [
    ("summarize", [r"\bsummariz(e|ing|ation)\b", r"\bsummaris(e|ing|ation)\b", r"\btldr\b", r"\bcondense\b", r"\babstract\b", r"\bshorten\b"], LLAMA_3_3_70B),
    ("translate", [r"\btranslate\b", r"\binto (english|spanish|french|german|hindi|japanese|korean|chinese)\b", r"\b(in|to) (en|es|fr|de|hi|ja|ko|zh)\b"], LLAMA_3_3_70B),
    ("code", [r"\bcode\b", r"\bdebug(ging)?\b", r"```", r"\bfunction\b", r"\bclass\b", r"\berror\b", r"\bstacktrace\b"], QWEN3_CODER),
    ("math", [r"\b\d+\s*[\+\-\*\/\^]\s*\d+\b", r"\bsolve\b", r"\bmath(ematics)?\b", r"\bderivative\b", r"\bintegral\b"], DEEPSEEK_R1),
    ("reasoning", [r"\breason(ing)?\b", r"\banalyze\b", r"\bthink\b", r"\bstep by step\b", r"\blogic\b"], DEEPSEEK_R1),
    ("fast", [r"\bfast\b", r"real-?time\b", r"\brealtime\b", r"\blatency\b", r"\bquick\b"], LLAMA_3_2_3B),
    ("creative", [r"\bcreative\b", r"\bstory\b", r"\bpoem\b", r"\bimagine\b", r"\bcharacter\b", r"\bscene\b", r"\bnarrative\b"], LLAMA_3_3_70B),
    ("vision", [r"\bimage\b", r"\bvision\b", r"\bpicture\b", r"\bphoto\b", r"\bscreenshot\b"], GEMINI_2_FLASH),  # Multimodal capable
    ("chat", [r"\bhello\b", r"\bhi\b", r"\bchat\b", r"\btalk\b", r"\bconvers(e|ation)\b"], LLAMA_3_2_3B),  # Fast for casual chat
]


def get_model_source(model_id: str) -> str:
    """Get model source with normalization"""
    norm = normalize_model_id(model_id)
    return MODEL_SOURCES.get(norm, MODEL_SOURCES.get(model_id, "OpenRouter"))


def get_fallback_chain(primary_model: str) -> List[str]:
    """Get normalized and deduplicated fallback chain"""
    raw_chain = FALLBACK_CHAINS.get(primary_model, [primary_model])
    seen = set()
    out = []
    for m in raw_chain:
        norm = normalize_model_id(m)
        if norm not in seen:
            seen.add(norm)
            out.append(norm)
    # if out empty, fallback to SAFE_DEFAULT_MODEL normalized
    if not out:
        out = [normalize_model_id(SAFE_DEFAULT_MODEL)]
    return out


def get_rule_keywords() -> List[Tuple[str, List[str], str]]:
    return RULE_KEYWORDS


__all__ = [
    "MODEL_SOURCES",
    "FALLBACK_CHAINS", 
    "INTENT_MODEL_MAPPING",
    "SAFE_DEFAULT_MODEL",
    "get_model_source",
    "get_fallback_chain",
    "get_rule_keywords",
    # === OpenRouter Free Tier Models ===
    # Reasoning specialists
    "DEEPSEEK_R1",
    "DEEPSEEK_R1_DISTILL", 
    # Chat & general purpose
    "LLAMA_3_3_70B",
    "LLAMA_3_1_405B",
    "LLAMA_3_2_3B",
    # Specialized models
    "QWEN3_CODER",
    "MISTRAL_NEMO",
    "GEMINI_2_FLASH",
    "GEMINI_2_5_PRO",
    # === Legacy OpenRouter model IDs ===
    "CLAUDE_SONNET",
    "CLAUDE_OPUS", 
    "CLAUDE_HAIKU",
    "GPT_4_TURBO",
    "GPT_4O",
    "GPT_35_TURBO",
    "MIXTRAL_8x7B_OR",
    "LLAMA3_70B_OR",
    "GEMINI_15_PRO",
    "GEMINI_15_FLASH",
    # === Groq model IDs (actual model names) ===
    "LLAMA3_8B_GROQ",
    "LLAMA3_70B_GROQ",
    "GEMMA2_9B",
    "DEEPSEEK_R1_GROQ",
    "QWEN3_32B",
    "MIXTRAL_8x7B_GROQ",
    "LLAMA3_VERSATILE",
]
