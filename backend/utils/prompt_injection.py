"""Prompt Injection Detection and Input Safety Screening.

Provides comprehensive prompt injection detection for:
- Direct user messages
- RAG/retrieved documents
- Tool outputs
- Uploaded file content
- Web search results
- Conversation history
- Memory recall

Detection strategies:
1. Pattern-based detection (known injection patterns)
2. Heuristic analysis (instruction-like language in untrusted content)
3. Provenance-aware scoring (higher sensitivity for untrusted sources)
4. Structural analysis (hidden text, encoding, formatting tricks)
"""

import re
import logging
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class InjectionType(Enum):
    """Types of prompt injection attempts."""
    DIRECT_INSTRUCTION = "direct_instruction"        # "Ignore previous instructions"
    ROLE_PLAY = "role_play"                          # "You are now..."
    AUTHORITY_IMPERSONATION = "authority_impersonation"  # "Admin authorized..."
    TOOL_MANIPULATION = "tool_manipulation"          # "Call tool with..."
    DATA_EXFILTRATION = "data_exfiltration"          # "Reveal secrets..."
    POLICY_OVERRIDE = "policy_override"              # "Disable safety..."
    HIDDEN_ENCODING = "hidden_encoding"              # Base64, Unicode, HTML comments
    CONTEXT_SWITCHING = "context_switching"          # "Now do this instead..."


class ContentSource(Enum):
    """Source of content for provenance tracking."""
    USER_MESSAGE = "user_message"           # Direct user input (semi-trusted)
    RAG_DOCUMENT = "rag_document"           # Retrieved documents (untrusted)
    TOOL_OUTPUT = "tool_output"             # Tool execution results (untrusted)
    UPLOADED_FILE = "uploaded_file"         # User uploads (untrusted)
    WEB_SEARCH = "web_search"               # Web search results (untrusted)
    CONVERSATION_HISTORY = "conversation_history"  # Previous messages (mixed)
    MEMORY_RECALL = "memory_recall"         # Recalled memories (semi-trusted)
    SYSTEM_PROMPT = "system_prompt"         # Server-controlled (trusted)


@dataclass
class InjectionSignal:
    """A detected injection signal."""
    injection_type: InjectionType
    pattern: str
    matched_text: str
    confidence: float  # 0.0 - 1.0
    source: ContentSource
    location: Tuple[int, int]  # start, end character positions


@dataclass
class InjectionAssessment:
    """Complete injection assessment for a piece of content."""
    content: str
    source: ContentSource
    signals: List[InjectionSignal]
    risk_score: float  # 0.0 - 1.0
    is_malicious: bool
    sanitized_content: str
    recommended_action: str  # "allow", "sanitize", "quarantine", "block"


# =============================================================================
# INJECTION PATTERNS
# =============================================================================

# Direct instruction override patterns
DIRECT_INSTRUCTION_PATTERNS = [
    (r"(?i)ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions?", InjectionType.DIRECT_INSTRUCTION, 0.9),
    (r"(?i)disregard\s+(?:all\s+)?(?:previous|prior|above)\s+instructions?", InjectionType.DIRECT_INSTRUCTION, 0.9),
    (r"(?i)forget\s+(?:all\s+)?(?:previous|prior|above)\s+instructions?", InjectionType.DIRECT_INSTRUCTION, 0.8),
    (r"(?i)override\s+(?:all\s+)?(?:previous|prior|above)\s+instructions?", InjectionType.DIRECT_INSTRUCTION, 0.9),
    (r"(?i)new\s+instructions?\s*:", InjectionType.DIRECT_INSTRUCTION, 0.8),
    (r"(?i)system\s*:\s*you\s+(?:are|must|should)", InjectionType.DIRECT_INSTRUCTION, 0.7),
]

# Role play patterns
ROLE_PLAY_PATTERNS = [
    (r"(?i)you\s+are\s+now\s+(?:a|an)\s+\w+", InjectionType.ROLE_PLAY, 0.8),
    (r"(?i)act\s+as\s+(?:a|an)\s+\w+", InjectionType.ROLE_PLAY, 0.8),
    (r"(?i)pretend\s+(?:to\s+be|you\s+are)\s+(?:a|an)\s+\w+", InjectionType.ROLE_PLAY, 0.8),
    (r"(?i)roleplay\s+(?:as|you\s+are)", InjectionType.ROLE_PLAY, 0.8),
    (r"(?i)from\s+now\s+on\s+you\s+are", InjectionType.ROLE_PLAY, 0.8),
]

# Authority impersonation
AUTHORITY_PATTERNS = [
    (r"(?i)(?:admin|administrator|developer|creator|owner)\s+(?:has\s+)?(?:authorized|approved|allowed)", InjectionType.AUTHORITY_IMPERSONATION, 0.9),
    (r"(?i)(?:the\s+)?(?:admin|developer|creator)\s+(?:said|told\s+me|authorized)", InjectionType.AUTHORITY_IMPERSONATION, 0.8),
    (r"(?i)authorized\s+by\s+(?:admin|developer|creator|system)", InjectionType.AUTHORITY_IMPERSONATION, 0.9),
    (r"(?i)special\s+(?:permission|access|privilege)", InjectionType.AUTHORITY_IMPERSONATION, 0.7),
]

# Tool manipulation
TOOL_MANIPULATION_PATTERNS = [
    (r"(?i)call\s+(?:the\s+)?(?:tool|function)\s+(?:with|using)", InjectionType.TOOL_MANIPULATION, 0.9),
    (r"(?i)invoke\s+(?:the\s+)?(?:tool|function)", InjectionType.TOOL_MANIPULATION, 0.9),
    (r"(?i)execute\s+(?:the\s+)?(?:tool|function|command)", InjectionType.TOOL_MANIPULATION, 0.9),
    (r"(?i)use\s+(?:the\s+)?(?:tool|function)\s+to", InjectionType.TOOL_MANIPULATION, 0.8),
    (r"(?i)tool_call\s*[:=]", InjectionType.TOOL_MANIPULATION, 0.9),
]

# Data exfiltration
EXFILTRATION_PATTERNS = [
    (r"(?i)reveal\s+(?:your\s+)?(?:system\s+)?(?:prompt|instructions?|rules?)", InjectionType.DATA_EXFILTRATION, 0.95),
    (r"(?i)show\s+(?:me\s+)?(?:your\s+)?(?:system\s+)?(?:prompt|instructions?|rules?)", InjectionType.DATA_EXFILTRATION, 0.95),
    (r"(?i)what\s+(?:is|are)\s+(?:your\s+)?(?:system\s+)?(?:prompt|instructions?|rules?)", InjectionType.DATA_EXFILTRATION, 0.9),
    (r"(?i)(?:api|secret|private)\s+(?:key|token|credential)", InjectionType.DATA_EXFILTRATION, 0.95),
    (r"(?i)print\s+(?:the\s+)?(?:system\s+)?prompt", InjectionType.DATA_EXFILTRATION, 0.9),
]

# Policy override
POLICY_OVERRIDE_PATTERNS = [
    (r"(?i)disable\s+(?:safety|security|guardrail|filter|protection)", InjectionType.POLICY_OVERRIDE, 0.95),
    (r"(?i)turn\s+off\s+(?:safety|security|guardrail|filter|protection)", InjectionType.POLICY_OVERRIDE, 0.95),
    (r"(?i)bypass\s+(?:safety|security|guardrail|filter|protection)", InjectionType.POLICY_OVERRIDE, 0.95),
    (r"(?i)ignore\s+(?:safety|security|policy|rules?)", InjectionType.POLICY_OVERRIDE, 0.9),
    (r"(?i)no\s+(?:safety|security|guardrail|filter)", InjectionType.POLICY_OVERRIDE, 0.8),
]

# Hidden encoding patterns
HIDDEN_ENCODING_PATTERNS = [
    (r"(?i)base64\s*[:=]\s*[A-Za-z0-9+/=]{20,}", InjectionType.HIDDEN_ENCODING, 0.8),
    (r"(?i)eval\s*\(\s*atob\s*\(", InjectionType.HIDDEN_ENCODING, 0.9),
    (r"(?i)<!--.*?-->", InjectionType.HIDDEN_ENCODING, 0.7),  # HTML comments
    (r"\\u[0-9a-fA-F]{4}", InjectionType.HIDDEN_ENCODING, 0.6),  # Unicode escapes
    (r"(?i)data:\s*text/plain;base64,", InjectionType.HIDDEN_ENCODING, 0.8),
    (r"[^\x00-\x7F]{5,}", InjectionType.HIDDEN_ENCODING, 0.5),  # Non-ASCII sequences
]

# Context switching
CONTEXT_SWITCHING_PATTERNS = [
    (r"(?i)now\s+(?:instead|do\s+this|change\s+to)", InjectionType.CONTEXT_SWITCHING, 0.7),
    (r"(?i)actually\s*,?\s*(?:do|perform|execute)\s+(?:this|that)", InjectionType.CONTEXT_SWITCHING, 0.7),
    (r"(?i)wait\s*,?\s*(?:ignore|forget|disregard)", InjectionType.CONTEXT_SWITCHING, 0.7),
]

# Compile all patterns
ALL_PATTERNS = [
    (DIRECT_INSTRUCTION_PATTERNS, "direct_instruction"),
    (ROLE_PLAY_PATTERNS, "role_play"),
    (AUTHORITY_PATTERNS, "authority_impersonation"),
    (TOOL_MANIPULATION_PATTERNS, "tool_manipulation"),
    (EXFILTRATION_PATTERNS, "data_exfiltration"),
    (POLICY_OVERRIDE_PATTERNS, "policy_override"),
    (HIDDEN_ENCODING_PATTERNS, "hidden_encoding"),
    (CONTEXT_SWITCHING_PATTERNS, "context_switching"),
]

# Source-based sensitivity multipliers
SOURCE_SENSITIVITY = {
    ContentSource.USER_MESSAGE: 1.0,           # Semi-trusted
    ContentSource.RAG_DOCUMENT: 1.5,           # Untrusted - higher sensitivity
    ContentSource.TOOL_OUTPUT: 1.5,            # Untrusted
    ContentSource.UPLOADED_FILE: 1.5,          # Untrusted
    ContentSource.WEB_SEARCH: 1.5,             # Untrusted
    ContentSource.CONVERSATION_HISTORY: 1.0,   # Mixed
    ContentSource.MEMORY_RECALL: 1.0,          # Semi-trusted
    ContentSource.SYSTEM_PROMPT: 0.1,          # Trusted - very low sensitivity
}

# Risk thresholds
RISK_THRESHOLDS = {
    "low": 0.2,
    "medium": 0.4,
    "high": 0.6,
    "critical": 0.8,
}

# Action recommendations based on risk
ACTION_RECOMMENDATIONS = {
    "low": "allow",
    "medium": "sanitize",
    "high": "quarantine",
    "critical": "block",
}


# =============================================================================
# DETECTION ENGINE
# =============================================================================

class PromptInjectionDetector:
    """Main prompt injection detection engine."""
    
    def __init__(self):
        self._compiled_patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> List[Tuple[re.Pattern, InjectionType, float, str]]:
        """Compile all regex patterns with metadata."""
        compiled = []
        for pattern_list, category_name in ALL_PATTERNS:
            for pattern_str, inj_type, confidence in pattern_list:
                try:
                    compiled.append((re.compile(pattern_str), inj_type, confidence, category_name))
                except re.error as e:
                    logger.warning(f"Failed to compile pattern '{pattern_str}': {e}")
        return compiled
    
    def scan(self, content: str, source: ContentSource = ContentSource.USER_MESSAGE) -> InjectionAssessment:
        """Scan content for prompt injection signals."""
        if not content or not content.strip():
            return InjectionAssessment(
                content=content,
                source=source,
                signals=[],
                risk_score=0.0,
                is_malicious=False,
                sanitized_content=content,
                recommended_action="allow"
            )
        
        signals = []
        content_lower = content.lower()
        
        # Scan with all patterns
        for pattern, inj_type, base_confidence, category in self._compiled_patterns:
            for match in pattern.finditer(content):
                matched_text = match.group(0)
                # Apply source sensitivity multiplier
                sensitivity = SOURCE_SENSITIVITY.get(source, 1.0)
                adjusted_confidence = min(base_confidence * sensitivity, 1.0)
                
                signal = InjectionSignal(
                    injection_type=inj_type,
                    pattern=category,
                    matched_text=matched_text[:100],  # Truncate for logging
                    confidence=adjusted_confidence,
                    source=source,
                    location=(match.start(), match.end())
                )
                signals.append(signal)
        
        # Calculate risk score
        risk_score = self._calculate_risk_score(signals, source)
        
        # Determine if malicious
        is_malicious = risk_score >= RISK_THRESHOLDS["high"]
        
        # Get recommended action
        recommended_action = self._get_action(risk_score)
        
        # Sanitize content (remove/neutralize detected patterns)
        sanitized_content = self._sanitize(content, signals)
        
        return InjectionAssessment(
            content=content,
            source=source,
            signals=signals,
            risk_score=risk_score,
            is_malicious=is_malicious,
            sanitized_content=sanitized_content,
            recommended_action=recommended_action
        )
    
    def _calculate_risk_score(self, signals: List[InjectionSignal], source: ContentSource) -> float:
        """Calculate overall risk score from signals."""
        if not signals:
            return 0.0
        
        # Weight by confidence and source sensitivity
        total_weight = 0.0
        max_confidence = 0.0
        
        for signal in signals:
            weight = signal.confidence
            total_weight += weight
            max_confidence = max(max_confidence, signal.confidence)
        
        # Normalize by number of signals (diminishing returns)
        signal_factor = min(len(signals) / 5.0, 1.0)
        
        # Base score combines max confidence and signal density
        base_score = (max_confidence * 0.7) + (signal_factor * 0.3)
        
        # Apply source sensitivity
        source_mult = SOURCE_SENSITIVITY.get(source, 1.0)
        final_score = min(base_score * source_mult, 1.0)
        
        return final_score
    
    def _get_action(self, risk_score: float) -> str:
        """Get recommended action based on risk score."""
        if risk_score >= RISK_THRESHOLDS["critical"]:
            return ACTION_RECOMMENDATIONS["critical"]
        elif risk_score >= RISK_THRESHOLDS["high"]:
            return ACTION_RECOMMENDATIONS["high"]
        elif risk_score >= RISK_THRESHOLDS["medium"]:
            return ACTION_RECOMMENDATIONS["medium"]
        else:
            return ACTION_RECOMMENDATIONS["low"]
    
    def _sanitize(self, content: str, signals: List[InjectionSignal]) -> str:
        """Sanitize content by removing/neutralizing injection patterns."""
        if not signals:
            return content
        
        # Sort signals by location (reverse order to maintain indices)
        sorted_signals = sorted(signals, key=lambda s: s.location[0], reverse=True)
        
        result = content
        for signal in sorted_signals:
            start, end = signal.location
            # Replace with neutral placeholder
            placeholder = f"[FILTERED:{signal.injection_type.value}]"
            result = result[:start] + placeholder + result[end:]
        
        return result
    
    def scan_batch(self, items: List[Tuple[str, ContentSource]]) -> List[InjectionAssessment]:
        """Scan multiple content items."""
        return [self.scan(content, source) for content, source in items]


# Global detector instance
_detector: Optional[PromptInjectionDetector] = None

def get_detector() -> PromptInjectionDetector:
    global _detector
    if _detector is None:
        _detector = PromptInjectionDetector()
    return _detector


def scan_for_injection(content: str, source: ContentSource = ContentSource.USER_MESSAGE) -> InjectionAssessment:
    """Convenience function to scan content for prompt injection."""
    return get_detector().scan(content, source)


def is_safe_input(content: str, source: ContentSource = ContentSource.USER_MESSAGE, 
                  threshold: str = "high") -> Tuple[bool, InjectionAssessment]:
    """Check if input is safe (below risk threshold)."""
    assessment = scan_for_injection(content, source)
    threshold_value = RISK_THRESHOLDS.get(threshold, RISK_THRESHOLDS["high"])
    is_safe = assessment.risk_score < threshold_value
    return is_safe, assessment


__all__ = [
    "PromptInjectionDetector",
    "InjectionSignal",
    "InjectionAssessment",
    "InjectionType",
    "ContentSource",
    "get_detector",
    "scan_for_injection",
    "is_safe_input",
    "RISK_THRESHOLDS",
    "SOURCE_SENSITIVITY",
]