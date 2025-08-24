"""
Kuro AI Utilities Package

This package provides core utilities for the Kuro AI chatbot including:
- Advanced prompt engineering and system instructions
- Safety validation and content filtering
- Response quality assessment and guardrails
- Retry mechanisms and fallback responses

Version: 2025-01-27 - Production utilities
"""

from .kuro_prompt import (
    build_kuro_prompt,
    sanitize_response,
    KuroPromptBuilder,
    KuroPromptConfig
)

from .safety import (
    validate_response,
    get_fallback_response,
    KuroSafetyValidator,
    KuroResponseValidator,
    SafetyLevel,
    ContentCategory
)

__all__ = [
    'build_kuro_prompt',
    'sanitize_response',
    'validate_response', 
    'get_fallback_response',
    'KuroPromptBuilder',
    'KuroPromptConfig',
    'KuroSafetyValidator',
    'KuroResponseValidator',
    'SafetyLevel',
    'ContentCategory'
]

__version__ = "1.0.0"
