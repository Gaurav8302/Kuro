"""
Token Counting Utilities for Groq LLaMA 3 70B Optimization

This module provides utilities for estimating and managing token usage
to ensure we stay within the 8K context limit.

Version: 2025-07-30 - Optimized for Groq LLaMA 3 70B
"""

import re
import logging
from typing import Dict, List, Any, Tuple

# Configure logging
logger = logging.getLogger(__name__)


class TokenCounter:
    """
    Token counting utility for LLaMA-based models
    
    Provides rough token estimation since we don't have access to
    the exact tokenizer used by Groq's LLaMA 3 70B.
    """
    
    # Rough token estimation constants
    CHARS_PER_TOKEN = 4  # Average characters per token for English text
    WORDS_PER_TOKEN = 0.75  # Average words per token
    
    @staticmethod
    def estimate_tokens_by_chars(text: str) -> int:
        """
        Estimate tokens based on character count
        
        Args:
            text (str): Text to estimate tokens for
            
        Returns:
            int: Estimated token count
        """
        if not text:
            return 0
        
        return max(1, len(text) // TokenCounter.CHARS_PER_TOKEN)
    
    @staticmethod
    def estimate_tokens_by_words(text: str) -> int:
        """
        Estimate tokens based on word count
        
        Args:
            text (str): Text to estimate tokens for
            
        Returns:
            int: Estimated token count
        """
        if not text:
            return 0
        
        # Simple word counting (splits on whitespace)
        words = len(text.split())
        return max(1, int(words / TokenCounter.WORDS_PER_TOKEN))
    
    @staticmethod
    def estimate_tokens(text: str, method: str = "chars") -> int:
        """
        Estimate token count using specified method
        
        Args:
            text (str): Text to estimate tokens for
            method (str): Estimation method ("chars", "words", or "hybrid")
            
        Returns:
            int: Estimated token count
        """
        if not text:
            return 0
        
        if method == "chars":
            return TokenCounter.estimate_tokens_by_chars(text)
        elif method == "words":
            return TokenCounter.estimate_tokens_by_words(text)
        elif method == "hybrid":
            # Use average of both methods
            char_estimate = TokenCounter.estimate_tokens_by_chars(text)
            word_estimate = TokenCounter.estimate_tokens_by_words(text)
            return (char_estimate + word_estimate) // 2
        else:
            # Default to character-based estimation
            return TokenCounter.estimate_tokens_by_chars(text)
    
    @staticmethod
    def truncate_to_token_limit(text: str, max_tokens: int, method: str = "chars") -> str:
        """
        Truncate text to fit within token limit
        
        Args:
            text (str): Text to truncate
            max_tokens (int): Maximum token count
            method (str): Estimation method
            
        Returns:
            str: Truncated text
        """
        if not text:
            return text
        
        current_tokens = TokenCounter.estimate_tokens(text, method)
        
        if current_tokens <= max_tokens:
            return text
        
        # Calculate approximate character limit
        if method == "chars":
            max_chars = max_tokens * TokenCounter.CHARS_PER_TOKEN
        elif method == "words":
            target_words = int(max_tokens * TokenCounter.WORDS_PER_TOKEN)
            words = text.split()
            if len(words) <= target_words:
                return text
            truncated_words = words[:target_words]
            return " ".join(truncated_words) + "..."
        else:  # hybrid or default
            max_chars = max_tokens * TokenCounter.CHARS_PER_TOKEN
        
        if len(text) <= max_chars:
            return text
        
        # Truncate and try to break at word boundary
        truncated = text[:max_chars-3]  # Reserve 3 chars for "..."
        
        # Try to break at last space to avoid cutting words
        last_space = truncated.rfind(' ')
        if last_space > max_chars * 0.8:  # Only if we don't lose too much text
            truncated = truncated[:last_space]
        
        return truncated + "..."
    
    @staticmethod
    def analyze_text_components(text: str) -> Dict[str, Any]:
        """
        Analyze text components for token estimation debugging
        
        Args:
            text (str): Text to analyze
            
        Returns:
            Dict[str, Any]: Analysis results
        """
        if not text:
            return {
                "char_count": 0,
                "word_count": 0,
                "token_estimate_chars": 0,
                "token_estimate_words": 0,
                "token_estimate_hybrid": 0
            }
        
        char_count = len(text)
        word_count = len(text.split())
        
        return {
            "char_count": char_count,
            "word_count": word_count,
            "token_estimate_chars": TokenCounter.estimate_tokens_by_chars(text),
            "token_estimate_words": TokenCounter.estimate_tokens_by_words(text),
            "token_estimate_hybrid": TokenCounter.estimate_tokens(text, "hybrid"),
            "avg_chars_per_word": char_count / max(1, word_count),
            "complexity_indicators": {
                "has_code": "```" in text or "`" in text,
                "has_numbers": bool(re.search(r'\d', text)),
                "has_punctuation": bool(re.search(r'[^\w\s]', text)),
                "has_special_chars": bool(re.search(r'[^\w\s.,!?;:]', text))
            }
        }


class ContextBuilder:
    """
    Helper class for building token-optimized context strings
    """
    
    def __init__(self, max_total_tokens: int = 7000):
        """
        Initialize context builder
        
        Args:
            max_total_tokens (int): Maximum total tokens allowed
        """
        self.max_total_tokens = max_total_tokens
        self.token_counter = TokenCounter()
    
    def build_optimized_context(
        self,
        components: List[Tuple[str, str, int]],  # (label, content, priority)
        user_message: str,
        reserve_tokens: int = 1500  # Reserve for system prompt + response
    ) -> Tuple[str, Dict[str, int]]:
        """
        Build optimized context by prioritizing components
        
        Args:
            components: List of (label, content, priority) tuples
            user_message: Current user message
            reserve_tokens: Tokens to reserve for system prompt and response
            
        Returns:
            Tuple[str, Dict[str, int]]: Context string and token breakdown
        """
        # Calculate available tokens
        user_message_tokens = self.token_counter.estimate_tokens(user_message)
        available_tokens = self.max_total_tokens - reserve_tokens - user_message_tokens
        
        # Sort components by priority (higher = more important)
        sorted_components = sorted(components, key=lambda x: x[2], reverse=True)
        
        # Build context within token limit
        selected_components = []
        used_tokens = 0
        token_breakdown = {"user_message": user_message_tokens}
        
        for label, content, priority in sorted_components:
            content_tokens = self.token_counter.estimate_tokens(content)
            
            if used_tokens + content_tokens <= available_tokens:
                selected_components.append((label, content))
                used_tokens += content_tokens
                token_breakdown[label] = content_tokens
            else:
                # Try to fit truncated version
                remaining_tokens = available_tokens - used_tokens
                if remaining_tokens > 50:  # Only if meaningful space left
                    truncated_content = self.token_counter.truncate_to_token_limit(
                        content, remaining_tokens
                    )
                    selected_components.append((label, truncated_content))
                    token_breakdown[label] = remaining_tokens
                    used_tokens = available_tokens
                break
        
        # Build final context string
        context_parts = []
        for label, content in selected_components:
            if content.strip():
                context_parts.append(f"{label}:\n{content}")
        
        context = "\n\n".join(context_parts)
        
        token_breakdown.update({
            "total_context": used_tokens,
            "reserved": reserve_tokens,
            "total_estimated": used_tokens + user_message_tokens + reserve_tokens,
            "remaining": max(0, self.max_total_tokens - (used_tokens + user_message_tokens + reserve_tokens))
        })
        
        return context, token_breakdown


# Convenience functions
def estimate_tokens(text: str) -> int:
    """Quick token estimation"""
    return TokenCounter.estimate_tokens(text)


def truncate_text(text: str, max_tokens: int) -> str:
    """Quick text truncation"""
    return TokenCounter.truncate_to_token_limit(text, max_tokens)


def analyze_prompt_size(
    system_prompt: str,
    context: str, 
    user_message: str,
    max_tokens: int = 7000
) -> Dict[str, Any]:
    """
    Analyze complete prompt size and provide recommendations
    
    Args:
        system_prompt: System/instruction prompt
        context: Context information
        user_message: User's message
        max_tokens: Maximum allowed tokens
        
    Returns:
        Dict: Analysis and recommendations
    """
    counter = TokenCounter()
    
    system_tokens = counter.estimate_tokens(system_prompt)
    context_tokens = counter.estimate_tokens(context)
    user_tokens = counter.estimate_tokens(user_message)
    total_tokens = system_tokens + context_tokens + user_tokens
    
    analysis = {
        "token_breakdown": {
            "system_prompt": system_tokens,
            "context": context_tokens,
            "user_message": user_tokens,
            "total": total_tokens
        },
        "limits": {
            "max_tokens": max_tokens,
            "remaining": max(0, max_tokens - total_tokens),
            "over_limit": total_tokens > max_tokens,
            "usage_percentage": (total_tokens / max_tokens) * 100
        },
        "recommendations": []
    }
    
    if total_tokens > max_tokens:
        excess = total_tokens - max_tokens
        analysis["recommendations"].append(f"Reduce input by {excess} tokens")
        
        if context_tokens > max_tokens * 0.4:
            analysis["recommendations"].append("Context is too large - consider summarization")
        
        if system_tokens > max_tokens * 0.2:
            analysis["recommendations"].append("System prompt may be too verbose")
    
    elif total_tokens > max_tokens * 0.9:
        analysis["recommendations"].append("Approaching token limit - monitor closely")
    
    return analysis
