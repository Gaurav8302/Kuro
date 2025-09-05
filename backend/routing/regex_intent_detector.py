"""Regex-based intent detection system for lightweight routing.

Replaces embedding-based similarity with comprehensive regex patterns
and keyword matching. Optimized for low memory usage and fast execution.
"""
from __future__ import annotations
import re
import logging
from typing import Dict, Set, List, Tuple, Optional
from functools import lru_cache

logger = logging.getLogger(__name__)

# Comprehensive intent patterns - optimized for accuracy
INTENT_PATTERNS = {
    "casual_chat": [
        # Greetings
        r'\b(?:hi|hello|hey|good\s+(?:morning|afternoon|evening|day)|greetings?)\b',
        r'\b(?:what\'?s\s+up|how\s+(?:are\s+you|ya\s+doing)|howdy)\b',
        r'\b(?:nice\s+to\s+meet\s+you|pleased\s+to\s+meet\s+you)\b',
        
        # Casual questions
        r'\b(?:how\s+(?:is|are)\s+(?:things?|it\s+going|you\s+doing))\b',
        r'\b(?:what\s+(?:have\s+you\s+been\s+up\s+to|are\s+you\s+up\s+to))\b',
        
        # Simple acknowledgments
        r'\b(?:ok|okay|cool|nice|great|awesome|thanks?|thank\s+you)\b$',
        
        # Weather/small talk
        r'\b(?:weather|nice\s+day|how\s+about\s+this\s+weather)\b',
    ],
    
    "complex_reasoning": [
        # Explicit reasoning requests
        r'\b(?:explain|analyze|break\s+down|walk\s+(?:me\s+)?through)\b',
        r'\b(?:step\s+by\s+step|detailed\s+(?:analysis|explanation))\b',
        r'\b(?:reasoning|logic|rationale|why\s+(?:is|does|would|should))\b',
        
        # Mathematical/logical problems
        r'\b(?:solve|calculate|compute|find\s+the\s+(?:answer|solution))\b',
        r'\b(?:proof|theorem|equation|formula|algorithm)\b',
        r'\b(?:if.*then|given.*find|assume.*prove)\b',
        
        # Analysis requests
        r'\b(?:compare|contrast|evaluate|assess|determine)\b',
        r'\b(?:pros\s+and\s+cons|advantages?\s+(?:and|vs)\s+disadvantages?)\b',
        r'\b(?:which\s+is\s+better|what\s+(?:are\s+the\s+)?(?:differences?|similarities))\b',
    ],
    
    "long_context_summary": [
        # Summarization requests
        r'\b(?:summarize|summary|sum\s+up|condense)\b',
        r'\b(?:main\s+points?|key\s+(?:points?|takeaways?|findings?))\b',
        r'\b(?:tldr|tl;dr|brief\s+(?:overview|summary)|in\s+short)\b',
        r'\b(?:gist|essence|core\s+(?:ideas?|concepts?))\b',
        
        # Document processing
        r'\b(?:this\s+(?:document|article|text|paper|report))\b.*\b(?:about|says?|means?)\b',
        r'\b(?:extract|identify|find).*(?:from\s+this|in\s+this)\b',
        
        # Long content indicators
        r'\b(?:long|lengthy|detailed|comprehensive)\s+(?:text|document|content)\b',
        r'(?:here\s+is|attached|following)\s+(?:a\s+)?(?:document|text|article)',
    ],
    
    "debugging": [
        # Error handling
        r'\b(?:debug|fix|solve|resolve)\b.*\b(?:error|bug|issue|problem)\b',
        r'\b(?:error|exception|traceback|stack\s+trace)\b',
        r'\b(?:not\s+working|broken|failing|crashed?)\b',
        
        # Code analysis
        r'\b(?:what\'?s\s+wrong\s+with|why\s+(?:isn\'?t|doesn\'?t))\b.*\b(?:code|function|script)\b',
        r'\b(?:syntax\s+error|runtime\s+error|logic\s+error)\b',
        r'\b(?:troubleshoot|diagnose)\b',
        
        # Specific tech problems
        r'\b(?:python|javascript|java|c\+\+|html|css)\b.*\b(?:error|problem|issue)\b',
    ],
    
    "tool_use_or_function_call": [
        # Function/API calls
        r'\b(?:call|execute|run|invoke)\s+(?:this\s+)?(?:function|method|api)\b',
        r'\b(?:use\s+the|make\s+a)\s+(?:api|tool|function|service)\b',
        r'\b(?:send\s+a\s+request|query\s+the\s+database)\b',
        
        # Command execution
        r'\b(?:execute|run)\s+(?:this\s+)?(?:command|script|program)\b',
        r'\b(?:shell|terminal|command\s+line)\b.*\b(?:run|execute)\b',
        
        # Integration requests
        r'\b(?:integrate\s+with|connect\s+to|fetch\s+from)\b',
    ],
    
    "high_creativity_generation": [
        # Creative writing
        r'\b(?:write|create|generate)\s+(?:a\s+)?(?:story|poem|script|song)\b',
        r'\b(?:creative|imaginative|original|unique)\b.*\b(?:content|writing|idea)\b',
        r'\b(?:brainstorm|come\s+up\s+with)\s+(?:ideas?|concepts?)\b',
        
        # Art/design
        r'\b(?:design|create)\s+(?:a\s+)?(?:logo|poster|layout|mockup)\b',
        r'\b(?:artistic|creative)\s+(?:direction|concept|vision)\b',
        
        # Fiction/narrative
        r'\b(?:tell\s+me\s+a\s+story|make\s+up|fiction|narrative)\b',
        r'\b(?:character|plot|setting|dialogue)\b',
    ],
    
    "teaching": [
        # Learning requests  
        r'\b(?:teach\s+me|learn\s+(?:about|how)|explain\s+(?:to\s+me\s+)?how)\b',
        r'\b(?:what\s+is|how\s+does|can\s+you\s+explain)\b',
        r'\b(?:tutorial|lesson|guide|instructions?)\b',
        
        # Understanding requests
        r'\b(?:understand|grasp|comprehend)\b.*\b(?:concept|idea|topic)\b',
        r'\b(?:help\s+me\s+(?:understand|learn)|show\s+me\s+how)\b',
        
        # Educational context
        r'\b(?:student|homework|assignment|study|exam)\b',
    ],
    
    "math_solver": [
        # Mathematical operations
        r'\b(?:\d+\s*[+\-*/]\s*\d+|calculate|solve)\b',
        r'\b(?:algebra|calculus|geometry|trigonometry|statistics)\b',
        r'\b(?:equation|formula|derivative|integral)\b',
        
        # Problem types
        r'\b(?:word\s+problem|math\s+problem|mathematical)\b',
        r'\b(?:percentage|fraction|decimal|ratio)\b',
        r'\b(?:graph|plot|chart)\b.*\b(?:function|data)\b',
    ]
}

# Keywords that boost intent confidence
INTENT_KEYWORDS = {
    "casual_chat": ["hello", "hi", "hey", "thanks", "cool", "nice", "weather"],
    "complex_reasoning": ["because", "therefore", "analyze", "explain", "reasoning", "logic"],
    "long_context_summary": ["summary", "tldr", "main", "key", "points", "overview"],
    "debugging": ["error", "bug", "fix", "debug", "broken", "traceback"],
    "tool_use_or_function_call": ["api", "function", "call", "execute", "run", "tool"],
    "high_creativity_generation": ["creative", "story", "write", "generate", "brainstorm"],
    "teaching": ["teach", "learn", "explain", "how", "tutorial", "lesson"],
    "math_solver": ["calculate", "solve", "math", "equation", "formula", "problem"]
}

# Context size indicators
SIZE_PATTERNS = {
    "short": r'\b(?:quick|brief|short|simple|small)\b',
    "medium": r'\b(?:moderate|regular|standard|normal)\b', 
    "long": r'\b(?:long|lengthy|detailed|comprehensive|extensive|large|big)\b'
}

class RegexIntentDetector:
    """Lightweight regex-based intent detection system."""
    
    def __init__(self):
        self._compiled_patterns = {}
        self._compiled_size_patterns = {}
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Pre-compile all regex patterns for performance."""
        for intent, patterns in INTENT_PATTERNS.items():
            self._compiled_patterns[intent] = [
                re.compile(pattern, re.IGNORECASE | re.MULTILINE)
                for pattern in patterns
            ]
        
        for size, pattern in SIZE_PATTERNS.items():
            self._compiled_size_patterns[size] = re.compile(pattern, re.IGNORECASE)
    
    @lru_cache(maxsize=512)
    def detect_intents(self, text: str, confidence_threshold: float = 0.3) -> Tuple[Set[str], Dict[str, float]]:
        """
        Detect intents from text using regex patterns and keyword matching.
        
        Args:
            text: Input text to analyze
            confidence_threshold: Minimum confidence to include intent
            
        Returns:
            Tuple of (detected_intents_set, confidence_scores_dict)
        """
        if not text or not text.strip():
            return set(), {}
        
        text_lower = text.lower()
        intent_scores = {}
        
        # Pattern matching
        for intent, compiled_patterns in self._compiled_patterns.items():
            score = 0.0
            pattern_matches = 0
            
            # Check regex patterns
            for pattern in compiled_patterns:
                matches = pattern.findall(text)
                if matches:
                    pattern_matches += len(matches)
                    score += 0.4 * len(matches)  # Base score per pattern match
            
            # Keyword boosting
            keywords = INTENT_KEYWORDS.get(intent, [])
            keyword_matches = sum(1 for keyword in keywords if keyword in text_lower)
            score += 0.2 * keyword_matches
            
            # Length normalization (avoid bias toward long texts)
            text_length = len(text.split())
            if text_length > 0:
                score = score * min(1.0, 20.0 / text_length)  # Normalize for texts longer than 20 words
            
            # Pattern density bonus (multiple different patterns matched)
            if pattern_matches > 1:
                score += 0.1
            
            intent_scores[intent] = score
        
        # Filter by confidence threshold
        detected_intents = {
            intent for intent, score in intent_scores.items() 
            if score >= confidence_threshold
        }
        
        return detected_intents, intent_scores
    
    def get_context_size_hint(self, text: str, context_tokens: int) -> str:
        """Determine context size category from text patterns and token count."""
        # Token-based classification (primary)
        if context_tokens > 15000:
            return "long"
        elif context_tokens > 5000:
            return "medium"
        elif context_tokens < 1000:
            return "short"
        
        # Pattern-based hints (secondary)
        for size, pattern in self._compiled_size_patterns.items():
            if pattern.search(text):
                return size
        
        return "medium"  # Default
    
    def get_message_metrics(self, text: str) -> Dict[str, int]:
        """Extract useful metrics from message text."""
        return {
            "char_count": len(text),
            "word_count": len(text.split()),
            "sentence_count": len(re.split(r'[.!?]+', text)),
            "line_count": len(text.split('\n')),
            "question_marks": text.count('?'),
            "exclamation_marks": text.count('!'),
        }

# Global singleton
_regex_detector = None

def get_regex_intent_detector() -> RegexIntentDetector:
    """Get global regex intent detector (singleton)."""
    global _regex_detector
    if _regex_detector is None:
        _regex_detector = RegexIntentDetector()
    return _regex_detector
