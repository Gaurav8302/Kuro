"""Embedding-based similarity matching for intelligent routing and skill detection.

Uses sentence-transformers/all-MiniLM-L6-v2 for lightweight, fast semantic similarity.
Provides fallback to cosine similarity if model fails to load.
"""
from __future__ import annotations
import logging
from typing import List, Dict, Optional, Tuple
import numpy as np
from functools import lru_cache
import os
import threading

logger = logging.getLogger(__name__)

class EmbeddingSimilarity:
    """Manages embedding model for semantic similarity matching."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", similarity_threshold: float = 0.65):
        self.model_name = model_name
        self.similarity_threshold = similarity_threshold
        self.model = None
        self._embeddings_cache: Dict[str, np.ndarray] = {}
        self._lock = threading.Lock()
        self._initialization_attempted = False
        
        # Don't initialize model at startup - wait until first use
        # This prevents blocking the startup process
    
    def _initialize_model(self):
        """Initialize sentence transformer model with error handling and timeout."""
        if self._initialization_attempted:
            return
            
        self._initialization_attempted = True
        
        try:
            # Skip initialization in production if disabled
            if os.getenv('DISABLE_EMBEDDINGS', 'false').lower() == 'true':
                logger.info("🚫 Embeddings disabled by environment variable")
                self.model = None
                return
            
            # Only import when actually needed to avoid startup delays
            from sentence_transformers import SentenceTransformer
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("Model loading timeout")
            
            # Use CPU to keep memory usage low for free tier deployments
            device = 'cpu'
            if os.getenv('EMBEDDING_DEVICE'):
                device = os.getenv('EMBEDDING_DEVICE')
            
            logger.info(f"Loading embedding model {self.model_name} on device: {device}")
            
            # Set a timeout for model loading (10 seconds max)
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(10)
            
            try:
                self.model = SentenceTransformer(self.model_name, device=device)
                signal.alarm(0)  # Cancel timeout
                logger.info("✅ Embedding model loaded successfully")
            except TimeoutError:
                logger.warning("⚠️ Model loading timeout, falling back to regex-only routing")
                self.model = None
            finally:
                signal.signal(signal.SIGALRM, old_handler)
            
        except ImportError:
            logger.warning("⚠️ sentence-transformers not available, semantic similarity disabled")
            self.model = None
        except Exception as e:
            logger.error(f"❌ Failed to load embedding model: {str(e)}")
            self.model = None
    
    @lru_cache(maxsize=1024)
    def get_embedding(self, text: str) -> Optional[np.ndarray]:
        """Get embedding for text with caching and lazy model loading."""
        # Initialize model on first use if not already attempted
        if not self._initialization_attempted:
            with self._lock:
                if not self._initialization_attempted:
                    self._initialize_model()
        
        if not self.model:
            return None
        
        try:
            # Clean and normalize text
            cleaned_text = text.lower().strip()[:512]  # Limit length for performance
            
            with self._lock:
                if cleaned_text in self._embeddings_cache:
                    return self._embeddings_cache[cleaned_text]
                
                embedding = self.model.encode(cleaned_text, convert_to_numpy=True)
                self._embeddings_cache[cleaned_text] = embedding
                
                # Keep cache size manageable
                if len(self._embeddings_cache) > 1000:
                    # Remove oldest 20% of entries
                    to_remove = len(self._embeddings_cache) // 5
                    keys_to_remove = list(self._embeddings_cache.keys())[:to_remove]
                    for key in keys_to_remove:
                        del self._embeddings_cache[key]
                
                return embedding
                
        except Exception as e:
            logger.warning(f"Failed to compute embedding for text: {str(e)}")
            return None
    
    def compute_similarity(self, text1: str, text2: str) -> float:
        """Compute cosine similarity between two texts."""
        emb1 = self.get_embedding(text1)
        emb2 = self.get_embedding(text2)
        
        if emb1 is None or emb2 is None:
            return 0.0
        
        try:
            # Cosine similarity
            dot_product = np.dot(emb1, emb2)
            norm_a = np.linalg.norm(emb1)
            norm_b = np.linalg.norm(emb2)
            
            if norm_a == 0 or norm_b == 0:
                return 0.0
            
            similarity = dot_product / (norm_a * norm_b)
            return float(similarity)
            
        except Exception as e:
            logger.warning(f"Failed to compute similarity: {str(e)}")
            return 0.0
    
    def find_best_matches(self, query: str, candidates: List[str], top_k: int = 3) -> List[Tuple[str, float]]:
        """Find top-k best matching candidates for a query."""
        if not candidates:
            return []
        
        similarities = []
        for candidate in candidates:
            similarity = self.compute_similarity(query, candidate)
            if similarity >= self.similarity_threshold:
                similarities.append((candidate, similarity))
        
        # Sort by similarity descending and return top-k
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
    
    def is_similar(self, text1: str, text2: str) -> bool:
        """Check if two texts are semantically similar above threshold."""
        similarity = self.compute_similarity(text1, text2)
        return similarity >= self.similarity_threshold
    
    def get_intent_similarity(self, query: str, intent_examples: Dict[str, List[str]]) -> List[Tuple[str, float]]:
        """Match query against intent examples and return scored intents."""
        intent_scores = []
        
        for intent, examples in intent_examples.items():
            max_similarity = 0.0
            
            for example in examples:
                similarity = self.compute_similarity(query, example)
                max_similarity = max(max_similarity, similarity)
            
            if max_similarity >= self.similarity_threshold:
                intent_scores.append((intent, max_similarity))
        
        # Sort by similarity descending
        intent_scores.sort(key=lambda x: x[1], reverse=True)
        return intent_scores


# Global singleton instance
_embedding_similarity = None
_init_lock = threading.Lock()

def get_embedding_similarity() -> EmbeddingSimilarity:
    """Get global embedding similarity instance (singleton)."""
    global _embedding_similarity
    
    if _embedding_similarity is None:
        with _init_lock:
            if _embedding_similarity is None:
                _embedding_similarity = EmbeddingSimilarity()
    
    return _embedding_similarity


# Intent examples for embedding-based matching
INTENT_EXAMPLES = {
    "casual_chat": [
        "hello there", "hi how are you", "good morning", "what's up", "hey", 
        "greetings", "nice to meet you", "how's it going"
    ],
    "complex_reasoning": [
        "explain step by step", "walk me through the logic", "help me understand why",
        "analyze this problem", "break down the reasoning", "logical explanation",
        "step by step solution", "detailed analysis"
    ],
    "long_context_summary": [
        "summarize this document", "give me the main points", "condense this text",
        "key takeaways from", "summary of this article", "tldr", "brief overview"
    ],
    "high_creativity_generation": [
        "write a story", "create something creative", "brainstorm ideas",
        "generate creative content", "storytelling", "creative writing",
        "imaginative response", "original ideas"
    ],
    "tool_use_or_function_call": [
        "call this function", "execute this command", "run this tool",
        "use the api", "make a request", "invoke function"
    ],
    "teaching": [
        "teach me about", "explain this concept", "how does this work",
        "educational explanation", "learn about", "tutorial on",
        "help me understand", "lesson on"
    ],
    "debugging": [
        "debug this error", "fix this bug", "troubleshoot", "what's wrong with",
        "error in my code", "help with this traceback", "code issue"
    ],
    "fact_checking": [
        "is this true", "verify this information", "fact check", "confirm this",
        "is this accurate", "validate this claim", "check if correct"
    ]
}
