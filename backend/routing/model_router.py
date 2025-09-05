"""Minimal model router for immediate deployment fix.

This is a simplified version that handles basic routing without
heavy dependencies to get the deployment working.
"""
from __future__ import annotations
import logging
import time
from typing import Optional, Dict, Any, Set, List

logger = logging.getLogger(__name__)

def route_model(message: str, context_tokens: int, intents: Optional[Set[str]] = None, 
                forced_model: Optional[str] = None, intent: Optional[str] = None,
                session_id: Optional[str] = None) -> Dict[str, Any]:
    """Minimal model routing function for deployment compatibility."""
    
    # Simple fallback to a safe default
    safe_default = "llama-3.3-70B-versatile"
    
    if forced_model:
        return {
            "model_id": forced_model,
            "rule": "forced_override",
            "explanation": f"Explicitly requested model: {forced_model}",
            "alternatives": [],
            "confidence": 1.0,
            "routing_data": {}
        }
    
    # Simple intent-based routing
    if intents:
        if "complex_reasoning" in intents or "debugging" in intents:
            return {
                "model_id": "llama-3.3-70B-versatile", 
                "rule": "intent_complex",
                "explanation": "Selected high-capability model for complex reasoning",
                "alternatives": [],
                "confidence": 0.8,
                "routing_data": {}
            }
        elif "casual_chat" in intents:
            return {
                "model_id": "llama-3.1-8b-instant",
                "rule": "intent_casual", 
                "explanation": "Selected fast model for casual chat",
                "alternatives": [],
                "confidence": 0.9,
                "routing_data": {}
            }
    
    # Fallback based on message length
    if len(message) > 500:
        model_id = "llama-3.3-70B-versatile"
        rule = "length_complex"
        explanation = "Selected high-capability model for long message"
    else:
        model_id = "llama-3.1-8b-instant"
        rule = "length_simple"
        explanation = "Selected fast model for short message"
    
    return {
        "model_id": model_id,
        "rule": rule,
        "explanation": explanation,
        "alternatives": [],
        "confidence": 0.7,
        "routing_data": {
            "message_length": len(message),
            "context_tokens": context_tokens
        }
    }

# Backward compatibility function
async def route_model_with_parallel_fallback(message: str, context_tokens: int, 
                                           session_id: Optional[str] = None,
                                           intents: Optional[Set[str]] = None) -> Dict[str, Any]:
    """Async wrapper for route_model for backward compatibility."""
    return route_model(message, context_tokens, intents=intents, session_id=session_id)
