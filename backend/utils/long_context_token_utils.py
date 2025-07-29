"""
Enhanced Token Utilities for LLaMA 3.3 70B Long-Context System

This module provides advanced token counting and management utilities
optimized for long-context models with 128K+ token capacity.

Features:
- Accurate token estimation for LLaMA 3.3 70B
- Intelligent text truncation preserving important information
- Memory-efficient processing for 512MB servers
- Context-aware token budgeting

Version: 2025-07-30 - Long-Context Optimization
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
import tiktoken

# Configure logging
logger = logging.getLogger(__name__)

class LongContextTokenManager:
    """
    Advanced token management for long-context LLaMA models
    
    Provides accurate token counting and intelligent truncation
    strategies for optimal prompt construction.
    """
    
    def __init__(self):
        """Initialize with LLaMA-compatible tokenizer"""
        try:
            # Use GPT-4 tokenizer as approximation for LLaMA 3.3
            self.tokenizer = tiktoken.encoding_for_model("gpt-4")
            logger.info("✅ Token manager initialized with GPT-4 tokenizer (LLaMA approximation)")
        except Exception as e:
            logger.warning(f"⚠️ Failed to load tokenizer, using fallback: {e}")
            self.tokenizer = None
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text using LLaMA-compatible tokenizer
        
        Args:
            text: Input text to count
            
        Returns:
            Number of tokens
        """
        if not text:
            return 0
        
        try:
            if self.tokenizer:
                return len(self.tokenizer.encode(text))
            else:
                # Fallback estimation: ~4 characters per token for English
                return max(1, len(text) // 4)
                
        except Exception as e:
            logger.warning(f"⚠️ Token counting failed, using fallback: {e}")
            return max(1, len(text) // 4)
    
    def truncate_preserving_structure(self, text: str, max_tokens: int, preserve_end: bool = True) -> str:
        """
        Intelligently truncate text while preserving structure
        
        Args:
            text: Text to truncate
            max_tokens: Maximum tokens allowed
            preserve_end: Whether to preserve the end (vs beginning)
            
        Returns:
            Truncated text
        """
        if not text or max_tokens <= 0:
            return ""
        
        current_tokens = self.count_tokens(text)
        
        if current_tokens <= max_tokens:
            return text
        
        # Split into sentences for better truncation
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        if preserve_end:
            # Keep the most recent sentences
            result_sentences = []
            total_tokens = 0
            
            for sentence in reversed(sentences):
                sentence_tokens = self.count_tokens(sentence)
                if total_tokens + sentence_tokens <= max_tokens:
                    result_sentences.insert(0, sentence)
                    total_tokens += sentence_tokens
                else:
                    break
            
            result = " ".join(result_sentences)
            
        else:
            # Keep the earliest sentences
            result_sentences = []
            total_tokens = 0
            
            for sentence in sentences:
                sentence_tokens = self.count_tokens(sentence)
                if total_tokens + sentence_tokens <= max_tokens:
                    result_sentences.append(sentence)
                    total_tokens += sentence_tokens
                else:
                    break
            
            result = " ".join(result_sentences)
        
        # Fallback to character-based truncation if sentence-based fails
        if not result or self.count_tokens(result) > max_tokens:
            if preserve_end:
                # Estimate character position and truncate from start
                char_ratio = len(text) / max(current_tokens, 1)
                approx_chars = int(max_tokens * char_ratio * 0.9)  # 90% safety margin
                result = "..." + text[-approx_chars:]
            else:
                # Truncate from end
                char_ratio = len(text) / max(current_tokens, 1)
                approx_chars = int(max_tokens * char_ratio * 0.9)
                result = text[:approx_chars] + "..."
        
        return result
    
    def optimize_conversation_tokens(
        self, 
        messages: List[Dict[str, str]], 
        max_tokens: int,
        preserve_recent: int = 3
    ) -> List[Dict[str, str]]:
        """
        Optimize conversation messages to fit token budget
        
        Args:
            messages: List of message dictionaries
            max_tokens: Maximum tokens for all messages
            preserve_recent: Number of recent messages to preserve fully
            
        Returns:
            Optimized message list
        """
        if not messages:
            return []
        
        # Always preserve the most recent messages fully
        recent_messages = messages[-preserve_recent:] if len(messages) > preserve_recent else messages
        older_messages = messages[:-preserve_recent] if len(messages) > preserve_recent else []
        
        # Count tokens in recent messages
        recent_tokens = sum(self.count_tokens(msg.get('content', '')) for msg in recent_messages)
        
        # Available tokens for older messages
        available_tokens = max_tokens - recent_tokens
        
        if available_tokens <= 0:
            # If recent messages exceed budget, truncate them
            logger.warning(f"⚠️ Recent messages exceed token budget ({recent_tokens} > {max_tokens})")
            optimized_recent = []
            remaining_tokens = max_tokens
            
            for msg in reversed(recent_messages):
                content = msg.get('content', '')
                content_tokens = self.count_tokens(content)
                
                if content_tokens <= remaining_tokens:
                    optimized_recent.insert(0, msg)
                    remaining_tokens -= content_tokens
                else:
                    # Truncate this message
                    truncated_content = self.truncate_preserving_structure(
                        content, remaining_tokens, preserve_end=True
                    )
                    if truncated_content:
                        truncated_msg = msg.copy()
                        truncated_msg['content'] = truncated_content
                        optimized_recent.insert(0, truncated_msg)
                    break
            
            return optimized_recent
        
        # Optimize older messages to fit remaining budget
        if not older_messages:
            return recent_messages
        
        # Summarize or truncate older messages
        optimized_older = []
        remaining_tokens = available_tokens
        
        for msg in reversed(older_messages):
            content = msg.get('content', '')
            content_tokens = self.count_tokens(content)
            
            if content_tokens <= remaining_tokens:
                optimized_older.insert(0, msg)
                remaining_tokens -= content_tokens
            else:
                # Try to truncate
                truncated_content = self.truncate_preserving_structure(
                    content, remaining_tokens, preserve_end=False
                )
                if truncated_content and self.count_tokens(truncated_content) > 10:  # Minimum viable length
                    truncated_msg = msg.copy()
                    truncated_msg['content'] = truncated_content
                    optimized_older.insert(0, truncated_msg)
                    break
                else:
                    # Skip this message if it can't be meaningfully truncated
                    break
        
        return optimized_older + recent_messages
    
    def calculate_response_budget(self, context_tokens: int, max_total: int = 128000) -> int:
        """
        Calculate available tokens for AI response
        
        Args:
            context_tokens: Tokens used in context/prompt
            max_total: Maximum total tokens for model
            
        Returns:
            Available tokens for response
        """
        # Reserve safety margin
        safety_margin = 1000
        available = max_total - context_tokens - safety_margin
        
        # Ensure minimum response length
        min_response = 500
        return max(min_response, available)
    
    def get_token_usage_breakdown(
        self, 
        system: str = "", 
        ltm: str = "", 
        stm: str = "", 
        user_message: str = ""
    ) -> Dict[str, int]:
        """
        Get detailed token usage breakdown
        
        Args:
            system: System instructions
            ltm: Long-term memory context  
            stm: Short-term memory context
            user_message: Current user message
            
        Returns:
            Dictionary with token counts
        """
        breakdown = {
            "system": self.count_tokens(system),
            "long_term_memory": self.count_tokens(ltm),
            "short_term_memory": self.count_tokens(stm),
            "user_message": self.count_tokens(user_message),
        }
        
        breakdown["total_context"] = sum(breakdown.values())
        breakdown["response_budget"] = self.calculate_response_budget(breakdown["total_context"])
        
        return breakdown

# Global instance for use throughout the application
long_context_token_manager = LongContextTokenManager()

def estimate_tokens(text: str) -> int:
    """
    Convenience function for token estimation
    
    Args:
        text: Text to count tokens for
        
    Returns:
        Estimated token count
    """
    return long_context_token_manager.count_tokens(text)

def truncate_to_token_limit(text: str, max_tokens: int, preserve_end: bool = True) -> str:
    """
    Convenience function for intelligent text truncation
    
    Args:
        text: Text to truncate
        max_tokens: Maximum tokens allowed
        preserve_end: Whether to preserve end vs beginning
        
    Returns:
        Truncated text
    """
    return long_context_token_manager.truncate_preserving_structure(text, max_tokens, preserve_end)

def optimize_messages_for_budget(
    messages: List[Dict[str, str]], 
    max_tokens: int, 
    preserve_recent: int = 3
) -> List[Dict[str, str]]:
    """
    Convenience function for message optimization
    
    Args:
        messages: List of conversation messages
        max_tokens: Token budget
        preserve_recent: Number of recent messages to preserve
        
    Returns:
        Optimized message list
    """
    return long_context_token_manager.optimize_conversation_tokens(messages, max_tokens, preserve_recent)

if __name__ == "__main__":
    # Test the token management system
    try:
        test_text = "This is a test message for token counting. " * 100
        token_count = estimate_tokens(test_text)
        print(f"✅ Token count test: {token_count} tokens")
        
        truncated = truncate_to_token_limit(test_text, 50)
        truncated_count = estimate_tokens(truncated)
        print(f"✅ Truncation test: {truncated_count} tokens")
        
    except Exception as e:
        print(f"❌ Token management test failed: {e}")
