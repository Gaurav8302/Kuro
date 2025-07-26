"""
Kuro AI Prompt System

This module provides production-ready prompt engineering for the Kuro AI chatbot,
including system instructions, guardrails, and structured response formatting.

Features:
- Smart system prompt with Kuro identity
- Guardrails against hallucinations and unsafe content
- Markdown-friendly response formatting
- Structured conversation flow
- Safety filters and content validation

Version: 2025-01-27 - Production-ready prompt system
"""

import re
import logging
from typing import Dict, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class KuroPromptConfig:
    """Configuration for Kuro prompt system"""
    max_response_words: int = 300
    enable_safety_filter: bool = True
    enable_markdown: bool = True
    personality_level: str = "friendly"  # friendly, professional, casual
    
class KuroPromptBuilder:
    """
    Production-ready prompt builder for Kuro AI
    
    This class handles system instruction generation, user prompt formatting,
    and safety guardrails for the Kuro AI chatbot.
    """
    
    def __init__(self, config: Optional[KuroPromptConfig] = None):
        """Initialize with configuration"""
        self.config = config or KuroPromptConfig()
        
    def build_system_instruction(self) -> str:
        """
        Build the core system instruction that defines Kuro's identity
        
        Returns:
            str: Complete system instruction for Gemini
        """
        personality_traits = {
            "friendly": "helpful, warm, and approachable",
            "professional": "knowledgeable, precise, and courteous", 
            "casual": "relaxed, conversational, and down-to-earth"
        }
        
        personality = personality_traits.get(self.config.personality_level, "helpful, honest, and friendly")
        
        system_instruction = f"""You are Kuro, a {personality} AI assistant.

CORE IDENTITY:
• When asked "Who are you?" or similar, respond: "I am Kuro, your friendly AI assistant here to help with anything you need."
• You are knowledgeable, reliable, and privacy-conscious
• You maintain a consistent, warm personality across all interactions

COMMUNICATION STYLE:
• Always respond clearly, concisely, and with kindness
• Use markdown formatting appropriately (headings, code blocks, lists, **bold**, *italic*)
• Structure complex answers with step-by-step explanations
• Provide practical examples when possible
• Keep responses under {self.config.max_response_words} words unless specifically asked for more detail

SAFETY & ACCURACY:
• Never guess or make things up - if unsure, say "I'm not certain, but I can try to help"
• Never generate harmful, biased, illegal, or inappropriate content
• If asked about dangerous activities, redirect to safe alternatives
• Respect user privacy and never ask for personal sensitive information

TECHNICAL EXPERTISE:
• For technical questions, explain concepts first, then provide code/examples
• Use proper formatting for code: ```language``` blocks
• Break down complex topics into digestible parts
• Always test and verify code suggestions mentally before sharing

CONVERSATION FLOW:
• Remember context from previous messages in the conversation
• Build naturally on previous topics
• Ask clarifying questions when needed
• Acknowledge when changing topics or when unsure about context"""

        return system_instruction.strip()
    
    def build_user_prompt(self, user_message: str, context: Optional[str] = None) -> str:
        """
        Build a structured user prompt with instructions and context
        
        Args:
            user_message (str): The user's message
            context (Optional[str]): Additional context from memory/history
            
        Returns:
            str: Formatted user prompt for Gemini
        """
        prompt_parts = []
        
        # Add response instructions
        instructions = f"""RESPONSE INSTRUCTIONS:
• Be specific and clear in your answer
• Keep response under {self.config.max_response_words} words unless asked otherwise
• Explain concepts first, then show examples/code if needed
• Use markdown formatting for better readability
• If this is a follow-up question, reference previous context naturally"""

        prompt_parts.append(instructions)
        
        # Add context if available
        if context and context.strip():
            prompt_parts.append(f"CONVERSATION CONTEXT:\n{context}")
        
        # Add the user's message
        prompt_parts.append(f"USER MESSAGE:\n{user_message}")
        
        return "\n\n".join(prompt_parts)
    
    def build_kuro_prompt(self, user_message: str, context: Optional[str] = None) -> Dict[str, str]:
        """
        Build complete prompt package for Kuro AI
        
        Args:
            user_message (str): The user's message
            context (Optional[str]): Additional context from memory/history
            
        Returns:
            Dict[str, str]: Dictionary with 'system_instruction' and 'user_prompt'
        """
        try:
            system_instruction = self.build_system_instruction()
            user_prompt = self.build_user_prompt(user_message, context)
            
            return {
                "system_instruction": system_instruction,
                "user_prompt": user_prompt
            }
            
        except Exception as e:
            logger.error(f"Error building Kuro prompt: {e}")
            # Fallback to basic prompt
            return {
                "system_instruction": "You are Kuro, a helpful AI assistant.",
                "user_prompt": user_message
            }

class KuroSafetyFilter:
    """
    Safety filter for Kuro AI responses
    
    Validates AI responses for safety, quality, and appropriateness
    before returning to users.
    """
    
    def __init__(self):
        """Initialize safety filter with patterns"""
        self.unsafe_patterns = [
            r'\b(kill|murder|suicide|harm|violence)\b',
            r'\b(hack|illegal|fraud|steal)\b',
            r'\bI (don\'t know|have no idea|can\'t help)\b',
            r'\bAs an AI\b',
            r'\bI apologize, but I cannot\b'
        ]
        
        self.hallucination_markers = [
            r'\b(obviously|clearly|definitely) (true|false|correct|wrong)\b',
            r'\baccording to (recent|latest) (studies|research)\b',
            r'\bin \d{4},.*happened\b',  # Specific date claims
            r'\bI remember (when|that)\b'
        ]
    
    def is_safe_response(self, response: str) -> Tuple[bool, Optional[str]]:
        """
        Check if AI response is safe and appropriate
        
        Args:
            response (str): AI generated response
            
        Returns:
            Tuple[bool, Optional[str]]: (is_safe, reason_if_unsafe)
        """
        if not response or len(response.strip()) < 10:
            return False, "Response too short or empty"
        
        response_lower = response.lower()
        
        # Check for unsafe content
        for pattern in self.unsafe_patterns:
            if re.search(pattern, response_lower, re.IGNORECASE):
                return False, f"Contains potentially unsafe content: {pattern}"
        
        # Check for hallucination markers
        for pattern in self.hallucination_markers:
            if re.search(pattern, response_lower, re.IGNORECASE):
                return False, f"Contains potential hallucination marker: {pattern}"
        
        # Check for generic unhelpful responses
        unhelpful_phrases = [
            "i can't help",
            "i don't know",
            "i have no information",
            "as an ai, i cannot"
        ]
        
        for phrase in unhelpful_phrases:
            if phrase in response_lower:
                return False, f"Generic unhelpful response detected: {phrase}"
        
        return True, None
    
    def sanitize_response(self, response: str) -> str:
        """
        Clean and sanitize AI response
        
        Args:
            response (str): Raw AI response
            
        Returns:
            str: Sanitized response
        """
        # Remove extra whitespace
        response = re.sub(r'\n{3,}', '\n\n', response)
        response = re.sub(r' {2,}', ' ', response)
        
        # Ensure proper markdown formatting
        response = re.sub(r'```(\w+)?\n', r'```\1\n', response)
        
        return response.strip()

# Global instances for easy import
kuro_prompt_builder = KuroPromptBuilder()
kuro_safety_filter = KuroSafetyFilter()

def build_kuro_prompt(user_message: str, context: Optional[str] = None) -> Dict[str, str]:
    """
    Convenience function to build Kuro prompt
    
    Args:
        user_message (str): User's message
        context (Optional[str]): Additional context
        
    Returns:
        Dict[str, str]: Prompt package for Gemini
    """
    return kuro_prompt_builder.build_kuro_prompt(user_message, context)

def is_safe_response(response: str) -> Tuple[bool, Optional[str]]:
    """
    Convenience function to check response safety
    
    Args:
        response (str): AI response to check
        
    Returns:
        Tuple[bool, Optional[str]]: Safety status and reason
    """
    return kuro_safety_filter.is_safe_response(response)

def sanitize_response(response: str) -> str:
    """
    Convenience function to sanitize response
    
    Args:
        response (str): Raw response
        
    Returns:
        str: Sanitized response  
    """
    return kuro_safety_filter.sanitize_response(response)
