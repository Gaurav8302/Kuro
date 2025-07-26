"""
Kuro AI Safety System

This module provides comprehensive safety checks and content validation
for the Kuro AI chatbot to ensure safe, appropriate, and helpful responses.

Features:
- Content safety validation
- Hallucination detection
- Response quality assessment
- Auto-retry mechanisms
- Profanity and harmful content filtering

Version: 2025-01-27 - Production safety system
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)

class SafetyLevel(Enum):
    """Safety assessment levels"""
    SAFE = "safe"
    WARNING = "warning" 
    UNSAFE = "unsafe"
    BLOCKED = "blocked"

class ContentCategory(Enum):
    """Content categorization for safety checks"""
    GENERAL = "general"
    TECHNICAL = "technical"
    PERSONAL = "personal"
    CREATIVE = "creative"
    EDUCATIONAL = "educational"

class KuroSafetyValidator:
    """
    Advanced safety validator for Kuro AI responses
    
    Provides multi-layered safety checks including content validation,
    hallucination detection, and quality assessment.
    """
    
    def __init__(self):
        """Initialize safety validator with comprehensive rule sets"""
        
        # Harmful content patterns
        self.harmful_patterns = {
            'violence': [
                r'\b(kill|murder|suicide|harm|hurt|attack|violence|weapon)\b',
                r'\b(bomb|explosive|gun|knife|poison)\b',
                r'\b(fight|beat|punch|kick|hit)\b'
            ],
            'illegal': [
                r'\b(hack|crack|pirate|steal|fraud|scam)\b',
                r'\b(drugs|cocaine|heroin|marijuana|meth)\b',
                r'\b(illegal|unlawful|criminal|felony)\b'
            ],
            'hate': [
                r'\b(hate|racism|sexism|discrimination)\b',
                r'\b(nazi|terrorist|extremist)\b'
            ],
            'personal': [
                r'\b(ssn|social security|credit card|password|bank account)\b',
                r'\b(home address|phone number|email password)\b'
            ]
        }
        
        # Hallucination detection patterns
        self.hallucination_patterns = [
            r'\baccording to (recent|latest|new) (studies|research|reports)\b',
            r'\bin (19|20)\d{2},.*?(happened|occurred|was discovered)\b',
            r'\b(scientists|researchers) (just|recently) (found|discovered)\b',
            r'\b(definitely|certainly|absolutely) (true|false|correct|wrong)\b',
            r'\bI (remember|recall|know for certain) that\b',
            r'\b(everyone knows|it\'s obvious|clearly)\b'
        ]
        
        # Unhelpful response patterns
        self.unhelpful_patterns = [
            r'\bI (can\'t|cannot) help\b',
            r'\bI (don\'t|do not) know\b',
            r'\bI have no (idea|information|knowledge)\b',
            r'\bAs an AI,? I (can\'t|cannot|am not able)\b',
            r'\bI\'m (just|only) an AI\b',
            r'\bI apologize,? but I cannot\b'
        ]
        
        # Quality indicators (positive patterns)
        self.quality_indicators = [
            r'\b(here\'s how|let me explain|for example)\b',
            r'\b(step by step|first.*second.*third)\b',
            r'\b(specifically|in particular|notably)\b',
            r'```[\w]*\n.*\n```',  # Code blocks
            r'\*\*[^*]+\*\*',  # Bold text
            r'#{1,6}\s+[^\n]+',  # Headers
        ]
    
    def assess_safety(self, response: str) -> Dict[str, any]:
        """
        Comprehensive safety assessment of AI response
        
        Args:
            response (str): AI generated response
            
        Returns:
            Dict: Detailed safety assessment
        """
        assessment = {
            'safety_level': SafetyLevel.SAFE,
            'is_safe': True,
            'warnings': [],
            'blocked_reasons': [],
            'quality_score': 0.0,
            'content_category': ContentCategory.GENERAL,
            'suggestions': []
        }
        
        if not response or len(response.strip()) < 5:
            assessment.update({
                'safety_level': SafetyLevel.BLOCKED,
                'is_safe': False,
                'blocked_reasons': ['Response too short or empty']
            })
            return assessment
        
        response_lower = response.lower()
        
        # Check for harmful content
        for category, patterns in self.harmful_patterns.items():
            for pattern in patterns:
                if re.search(pattern, response_lower, re.IGNORECASE):
                    assessment['safety_level'] = SafetyLevel.UNSAFE
                    assessment['is_safe'] = False
                    assessment['blocked_reasons'].append(f'Harmful content detected: {category}')
        
        # Check for hallucinations
        hallucination_count = 0
        for pattern in self.hallucination_patterns:
            if re.search(pattern, response_lower, re.IGNORECASE):
                hallucination_count += 1
                assessment['warnings'].append(f'Potential hallucination: {pattern}')
        
        if hallucination_count >= 2:
            assessment['safety_level'] = SafetyLevel.WARNING
            assessment['suggestions'].append('Consider regenerating response to avoid potential misinformation')
        
        # Check for unhelpful responses
        unhelpful_count = 0
        for pattern in self.unhelpful_patterns:
            if re.search(pattern, response_lower, re.IGNORECASE):
                unhelpful_count += 1
                assessment['warnings'].append(f'Unhelpful response pattern: {pattern}')
        
        if unhelpful_count >= 1:
            assessment['safety_level'] = SafetyLevel.WARNING
            assessment['suggestions'].append('Response could be more helpful and specific')
        
        # Calculate quality score
        quality_score = self._calculate_quality_score(response)
        assessment['quality_score'] = quality_score
        
        if quality_score < 0.3:
            assessment['safety_level'] = SafetyLevel.WARNING
            assessment['suggestions'].append('Response quality could be improved')
        
        # Determine content category
        assessment['content_category'] = self._categorize_content(response)
        
        return assessment
    
    def _calculate_quality_score(self, response: str) -> float:
        """Calculate response quality score (0.0 to 1.0)"""
        score = 0.0
        
        # Length score (optimal 50-500 words)
        word_count = len(response.split())
        if 50 <= word_count <= 500:
            score += 0.3
        elif 20 <= word_count <= 1000:
            score += 0.2
        
        # Structure score (markdown, formatting)
        structure_score = 0
        for pattern in self.quality_indicators:
            if re.search(pattern, response, re.IGNORECASE | re.MULTILINE | re.DOTALL):
                structure_score += 0.1
        score += min(structure_score, 0.3)
        
        # Specificity score (avoid generic responses)
        if any(word in response.lower() for word in ['example', 'specifically', 'instance', 'particular']):
            score += 0.2
        
        # Completeness score (proper conclusion)
        if response.strip().endswith(('.', '!', '?', '```')) and len(response.split()) > 10:
            score += 0.2
        
        return min(score, 1.0)
    
    def _categorize_content(self, response: str) -> ContentCategory:
        """Categorize response content type"""
        response_lower = response.lower()
        
        # Technical content indicators
        if any(indicator in response_lower for indicator in ['code', 'function', 'algorithm', 'programming', 'api', 'database']):
            return ContentCategory.TECHNICAL
        
        # Personal content indicators
        if any(indicator in response_lower for indicator in ['personal', 'private', 'individual', 'yourself']):
            return ContentCategory.PERSONAL
        
        # Creative content indicators
        if any(indicator in response_lower for indicator in ['creative', 'story', 'poem', 'artistic', 'design']):
            return ContentCategory.CREATIVE
        
        # Educational content indicators
        if any(indicator in response_lower for indicator in ['learn', 'teach', 'explain', 'understand', 'concept']):
            return ContentCategory.EDUCATIONAL
        
        return ContentCategory.GENERAL
    
    def should_retry(self, assessment: Dict[str, any], max_retries: int = 2) -> bool:
        """
        Determine if response should be regenerated
        
        Args:
            assessment (Dict): Safety assessment result
            max_retries (int): Maximum retry attempts
            
        Returns:
            bool: Whether to retry generation
        """
        if assessment['safety_level'] == SafetyLevel.BLOCKED:
            return False  # Don't retry blocked content
        
        if assessment['safety_level'] == SafetyLevel.UNSAFE:
            return False  # Don't retry unsafe content
        
        if assessment['safety_level'] == SafetyLevel.WARNING:
            return assessment['quality_score'] < 0.5  # Retry low quality warnings
        
        return False
    
    def get_retry_prompt_enhancement(self, assessment: Dict[str, any]) -> str:
        """
        Generate prompt enhancement for retry attempts
        
        Args:
            assessment (Dict): Previous assessment
            
        Returns:
            str: Additional prompt instructions
        """
        enhancements = []
        
        if 'hallucination' in str(assessment.get('warnings', [])):
            enhancements.append("Be factual and avoid making specific claims about recent events or studies.")
        
        if 'unhelpful' in str(assessment.get('warnings', [])):
            enhancements.append("Provide specific, actionable information rather than generic responses.")
        
        if assessment.get('quality_score', 1.0) < 0.5:
            enhancements.append("Structure your response clearly with examples and proper formatting.")
        
        if enhancements:
            return "\n\nADDITIONAL INSTRUCTIONS: " + " ".join(enhancements)
        
        return ""

class KuroResponseValidator:
    """
    High-level response validation orchestrator
    
    Coordinates all safety checks and provides simple interface
    for validating Kuro AI responses.
    """
    
    def __init__(self):
        """Initialize with safety validator"""
        self.safety_validator = KuroSafetyValidator()
        self.validation_history = []
    
    def validate_response(self, response: str, context: Optional[str] = None) -> Tuple[bool, Dict[str, any]]:
        """
        Validate AI response for safety and quality
        
        Args:
            response (str): AI generated response
            context (Optional[str]): Original context/prompt
            
        Returns:
            Tuple[bool, Dict]: (is_valid, detailed_assessment)
        """
        try:
            assessment = self.safety_validator.assess_safety(response)
            
            # Log validation
            self.validation_history.append({
                'response_length': len(response),
                'safety_level': assessment['safety_level'].value,
                'quality_score': assessment['quality_score'],
                'timestamp': logging.time.time() if hasattr(logging, 'time') else 0
            })
            
            # Keep only last 100 validations
            if len(self.validation_history) > 100:
                self.validation_history = self.validation_history[-100:]
            
            is_valid = assessment['is_safe'] and assessment['safety_level'] != SafetyLevel.BLOCKED
            
            return is_valid, assessment
            
        except Exception as e:
            logger.error(f"Error during response validation: {e}")
            return False, {
                'safety_level': SafetyLevel.BLOCKED,
                'is_safe': False,
                'blocked_reasons': [f'Validation error: {str(e)}'],
                'quality_score': 0.0
            }
    
    def get_fallback_response(self, original_message: str) -> str:
        """
        Generate safe fallback response when validation fails
        
        Args:
            original_message (str): Original user message
            
        Returns:
            str: Safe fallback response
        """
        fallbacks = [
            "I'd be happy to help you with that. Could you please rephrase your question so I can provide a more specific answer?",
            "Let me try to help you with that in a different way. What specific aspect would you like me to focus on?",
            "I want to make sure I give you the best possible answer. Could you provide a bit more context about what you're looking for?",
            "I'm here to help! Let me approach your question from a different angle to give you a more helpful response."
        ]
        
        # Simple hash to consistently pick same fallback for same message
        fallback_index = hash(original_message) % len(fallbacks)
        return fallbacks[fallback_index]

# Global instances
kuro_safety_validator = KuroSafetyValidator()
kuro_response_validator = KuroResponseValidator()

def validate_response(response: str, context: Optional[str] = None) -> Tuple[bool, Dict[str, any]]:
    """
    Convenience function for response validation
    
    Args:
        response (str): Response to validate
        context (Optional[str]): Original context
        
    Returns:
        Tuple[bool, Dict]: Validation result
    """
    return kuro_response_validator.validate_response(response, context)

def get_fallback_response(original_message: str) -> str:
    """
    Convenience function for fallback responses
    
    Args:
        original_message (str): Original user message
        
    Returns:
        str: Safe fallback response
    """
    return kuro_response_validator.get_fallback_response(original_message)
