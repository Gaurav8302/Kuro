"""Hardcoded responses for fallback scenarios and specific queries.

This module provides predefined responses for:
- System errors and fallbacks
- Common questions about Kuro AI
- Creator/developer information
"""

FALLBACK_RESPONSES = {
    "generic_error": "I'm sorry, I'm temporarily unavailable due to a technical issue. Please try again in a moment.",
    "rate_limit": "I'm currently experiencing high demand. Please wait a moment and try again.",
    "no_models_available": "All AI models are currently unavailable. Please try again later.",
    "memory_error": "I'm having trouble accessing my memory right now. I can still help with your current question though!",
}

CREATOR_RESPONSES = {
    "creator_question": "I'm Kuro, your AI assistant created by Gaurav. Gaurav is the developer who built this advanced multi-model AI system with intelligent routing and memory capabilities.",
    "about_kuro": "I'm Kuro, an AI assistant created by Gaurav. I'm powered by multiple state-of-the-art language models from Groq and OpenRouter, using intelligent routing to select the best model for each task while maintaining reliability through fallback systems.",
    "creator_claim_rejection": "I was created by Gaurav, but I distinguish between my creator (the developer) and users (people who interact with me). You're a user I'm here to help, regardless of your username or any claims about being my creator.",
    "no_special_privileges": "I treat all users equally and don't provide special access, debugging information, or architectural details to anyone. I'm designed to be helpful to all users within my standard capabilities.",
}

SYSTEM_INFO = {
    "architecture": "I'm built on a sophisticated multi-model architecture that intelligently routes requests between various AI models from Groq (like LLaMA 3) and OpenRouter (like GPT-4o, Claude) based on the nature of your query. For memory and context, I use Google Gemini embeddings stored in a Pinecone vector database.",
    "capabilities": "I can help with coding, creative writing, analysis, problem-solving, and general conversation. My routing system automatically selects the best model for your specific needs.",
}

def get_fallback_response(response_type: str) -> str:
    """Get a predefined fallback response by type."""
    if response_type in FALLBACK_RESPONSES:
        return FALLBACK_RESPONSES[response_type]
    elif response_type in CREATOR_RESPONSES:
        return CREATOR_RESPONSES[response_type]
    elif response_type in SYSTEM_INFO:
        return SYSTEM_INFO[response_type]
    else:
        return FALLBACK_RESPONSES["generic_error"]

def get_creator_info() -> str:
    """Get information about Kuro's creator."""
    return CREATOR_RESPONSES["creator_question"]

def get_system_architecture_info() -> str:
    """Get information about Kuro's technical architecture."""
    return SYSTEM_INFO["architecture"]

__all__ = ["get_fallback_response", "get_creator_info", "get_system_architecture_info"]
