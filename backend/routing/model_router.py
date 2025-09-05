"""Lightweight Model router with regex-based intent detection and rule-based routing.

Features:
- Comprehensive regex-based intent detection
- Rule-based routing with context awareness  
- Latency-aware routing with EMA tracking
- Session-aware adaptations (lightweight)
- Explainable routing decisions
- Fast fallback for critical intents

Exposed function: route_model(message: str, context_tokens: int, intents: Set[str] | None, session_id: str | None) -> dict
Returns: { 'model_id': str, 'rule': str, 'explanation': str, 'alternatives': list, 'confidence': float }
"""
from __future__ import annotations
import re
import logging
import time
from typing import Optional, Dict, Any, Set, List, Tuple
from config.config_loader import get_routing_rules, list_models, get_model
from config.model_config import normalize_model_id
from routing.regex_intent_detector import get_regex_intent_detector
from routing.latency_tracker import get_latency_tracker
from routing.session_tracker import get_session_manager

logger = logging.getLogger(__name__)

SAFE_DEFAULT = normalize_model_id("llama-3.3-70B-versatile")
CRITICAL_INTENTS = {"complex_reasoning", "debugging", "long_context_summary"}
CONFIDENCE_THRESHOLD = 0.5  # If top 2 models differ by less than this, pick faster one

def _regex_intent_detection(message: str, existing_intents: Optional[Set[str]] = None) -> Tuple[Set[str], List[str]]:
    """Regex-based intent detection with comprehensive pattern matching.
    
    Returns:
        Tuple of (detected_intents, explanations)
    """
    detected_intents = set(existing_intents) if existing_intents else set()
    explanations = []
    
    # Get regex intent detector
    regex_detector = get_regex_intent_detector()
    
    # Detect intents using regex patterns
    new_intents, confidence_scores = regex_detector.detect_intents(message)
    
    for intent in new_intents:
        detected_intents.add(intent)
        confidence = confidence_scores.get(intent, 0.0)
        explanations.append(f"regex_intent:{intent}(conf={confidence:.2f})")
    
    # Legacy regex patterns (keeping for backward compatibility)
    legacy_patterns = {
        "casual_chat": [
            r'\b(?:hi|hello|hey|good\s+(?:morning|afternoon|evening)|greetings?)\b',
            r'\b(?:thanks?|thank\s+you|ok|okay|cool|nice|great)\b$'
        ],
        "complex_reasoning": [
            r'\b(?:explain|analyze|why|how\s+(?:does|do|can|would))\b.*\b(?:work|happen|solve)\b',
            r'\b(?:step\s+by\s+step|detailed|reasoning|logic)\b'
        ],
        "debugging": [
            r'\b(?:error|bug|fix|debug|broken|not\s+working)\b',
            r'\b(?:exception|traceback|syntax\s+error)\b'
        ],
        "long_context_summary": [
            r'\b(?:summarize|summary|tldr|main\s+points?)\b',
            r'\b(?:condense|brief\s+overview|key\s+takeaways?)\b'
        ]
    }
    
    for intent, patterns in legacy_patterns.items():
        for pattern in patterns:
            if re.search(pattern, message, re.IGNORECASE):
                if intent not in detected_intents:
                    detected_intents.add(intent)
                    explanations.append(f"legacy_regex:{intent}")
                break
    
    return detected_intents, explanations

def _score_model_enhanced(model: Dict[str, Any], intents: Set[str], context_tokens: int, 
                         session_id: Optional[str] = None) -> Tuple[float, List[str]]:
    """Enhanced model scoring with latency, session preferences, and explainable reasoning."""
    score = 0.0
    explanations = []
    
    # Base capability scoring
    caps = set(model.get("capabilities", []))
    intent_mapping = {
        "casual_chat": "general",
        "long_context_summary": "long_context", 
        "complex_reasoning": "reasoning",
        "debugging": "reasoning",
        "tool_use_or_function_call": "tool_use",
        "high_creativity_generation": "high_quality",
    }
    
    for intent in intents:
        cap = intent_mapping.get(intent)
        if cap and cap in caps:
            score += 5.0
            explanations.append(f"capability_match:{intent}->{cap}(+5.0)")
    
    # Context token compatibility
    max_context = model.get("context_window", 8192)
    if context_tokens <= max_context:
        context_ratio = context_tokens / max_context
        if context_ratio > 0.8:
            score += 3.0
            explanations.append(f"high_context_fit({context_ratio:.1%},+3.0)")
        elif context_ratio > 0.5:
            score += 1.0
            explanations.append(f"med_context_fit({context_ratio:.1%},+1.0)")
    else:
        # Penalty for exceeding context window
        score -= 10.0
        explanations.append(f"context_exceeded({context_tokens}>{max_context},-10.0)")
    
    # Latency bonus (faster models get higher scores)
    latency_tracker = get_latency_tracker()
    model_id = model.get("id", "unknown")
    avg_latency = latency_tracker.get_average_latency(model_id)
    
    if avg_latency is not None:
        # Lower latency = higher score (max bonus: 2.0)
        latency_bonus = max(0, min(2.0, (3000 - avg_latency) / 1000))
        score += latency_bonus
        explanations.append(f"latency_bonus({avg_latency:.0f}ms,+{latency_bonus:.1f})")
    
    # Session preferences (lightweight version)
    if session_id:
        session_mgr = get_session_manager()
        preferred_models = session_mgr.get_preferred_models(session_id)
        if model_id in preferred_models:
            score += 1.0
            explanations.append(f"session_preference(+1.0)")
    
    # Provider preference (slight bias toward reliable providers)
    provider = model.get("provider", "").lower()
    provider_bonuses = {
        "groq": 0.5,      # Fast and reliable
        "openrouter": 0.3, # Good variety
        "google": 0.4      # High quality
    }
    if provider in provider_bonuses:
        bonus = provider_bonuses[provider]
        score += bonus
        explanations.append(f"provider_bonus:{provider}(+{bonus})")
    
    return score, explanations

def _select_best_models(models: List[Dict[str, Any]], intents: Set[str], 
                       context_tokens: int, session_id: Optional[str] = None,
                       top_k: int = 3) -> List[Tuple[Dict[str, Any], float, List[str]]]:
    """Select and score top-k models based on multiple factors."""
    scored_models = []
    
    for model in models:
        try:
            score, explanations = _score_model_enhanced(model, intents, context_tokens, session_id)
            scored_models.append((model, score, explanations))
        except Exception as e:
            logger.warning(f"Error scoring model {model.get('id', 'unknown')}: {str(e)}")
            continue
    
    # Sort by score (descending) and return top-k
    scored_models.sort(key=lambda x: x[1], reverse=True)
    return scored_models[:top_k]

def _check_confidence_threshold(scored_models: List[Tuple[Dict[str, Any], float, List[str]]]) -> Tuple[Dict[str, Any], str]:
    """Check if top model choice is confident enough, otherwise pick fastest."""
    if len(scored_models) < 2:
        return scored_models[0][0], "single_option"
    
    top_score = scored_models[0][1]
    second_score = scored_models[1][1]
    score_diff = top_score - second_score
    
    if score_diff < CONFIDENCE_THRESHOLD:
        # Scores are close, pick the faster model
        top_model = scored_models[0][0]
        second_model = scored_models[1][0]
        
        # Get latency data
        latency_tracker = get_latency_tracker()
        top_latency = latency_tracker.get_average_latency(top_model.get("id"))
        second_latency = latency_tracker.get_average_latency(second_model.get("id"))
        
        if top_latency and second_latency and second_latency < top_latency:
            return second_model, f"low_confidence_pick_faster(diff={score_diff:.1f})"
        else:
            return top_model, f"low_confidence_keep_top(diff={score_diff:.1f})"
    
    return scored_models[0][0], f"confident_choice(diff={score_diff:.1f})"

def route_model(message: str, context_tokens: int, intents: Optional[Set[str]] = None, 
                forced_model: Optional[str] = None, intent: Optional[str] = None,
                session_id: Optional[str] = None) -> Dict[str, Any]:
    """Lightweight model routing with regex-based detection and explainable decisions.
    
    Args:
        message: User message text
        context_tokens: Estimated context size
        intents: Pre-detected intents (optional)
        forced_model: Override model selection (optional)  
        intent: Legacy single intent support (optional)
        session_id: Session identifier for adaptive behavior (optional)
        
    Returns:
        Dict with model_id, rule, explanation, alternatives, confidence, and routing_data
    """
    start_time = time.time()
    routing_data = {
        'message_length': len(message),
        'context_tokens': context_tokens,
        'session_id': session_id,
        'timestamp': start_time
    }
    
    # Back-compat: merge single intent into intents set
    if intent and not intents:
        intents = {intent}
    
    # Handle forced model override
    if forced_model:
        forced_normalized = normalize_model_id(forced_model)
        logger.info(f"Using forced model: {forced_normalized}")
        return {
            "model_id": forced_normalized,
            "rule": "forced_override",
            "explanation": f"Explicitly requested model: {forced_normalized}",
            "alternatives": [],
            "confidence": 1.0,
            "routing_data": routing_data
        }
    
    # Step 1: Intent detection
    try:
        detected_intents, intent_explanations = _regex_intent_detection(message, intents)
        routing_data['detected_intents'] = list(detected_intents)
        routing_data['intent_explanations'] = intent_explanations
        
        logger.debug(f"Detected intents: {detected_intents}")
    except Exception as e:
        logger.error(f"Intent detection failed: {str(e)}")
        detected_intents = intents or set()
        intent_explanations = [f"intent_detection_error: {str(e)}"]
    
    # Step 2: Try rule-based routing first
    try:
        rules = get_routing_rules()
        logger.debug("Evaluating %d routing rules", len(rules))
    except Exception as e:
        logger.error("Failed to load routing rules: %s", str(e))
        return {
            "model_id": SAFE_DEFAULT,
            "rule": "rules_load_error", 
            "explanation": f"Could not load routing rules: {str(e)}",
            "alternatives": [],
            "confidence": 0.0,
            "routing_data": routing_data
        }
    
    # Rule-based matching with boost scoring
    for rule in rules:
        try:
            r_intent = rule.get("intent")
            chosen = rule.get("choose", SAFE_DEFAULT)
            chosen_norm = normalize_model_id(chosen)
            
            # Intent-based matching with rule boost
            if r_intent and r_intent in detected_intents:
                logger.info(f"Rule match: intent='{r_intent}' -> {chosen_norm}")
                return {
                    "model_id": chosen_norm,
                    "rule": f"intent_rule:{rule.get('name', 'unnamed')}",
                    "explanation": f"Matched intent '{r_intent}' rule: {rule.get('name', 'unnamed')}",
                    "alternatives": [],
                    "confidence": 0.9,
                    "routing_data": routing_data
                }
            
            # Condition-based matching
            condition = rule.get("condition")
            if condition:
                try:
                    # Build evaluation context
                    eval_context = {
                        'context_tokens': context_tokens,
                        'message_len_chars': len(message),
                        'has_intent': lambda x: x in detected_intents,
                        'word_count': len(message.split())
                    }
                    
                    # Evaluate condition safely
                    if eval(condition, {"__builtins__": {}}, eval_context):
                        logger.info(f"Rule match: condition='{condition}' -> {chosen_norm}")
                        return {
                            "model_id": chosen_norm,
                            "rule": f"condition_rule:{rule.get('name', 'unnamed')}",
                            "explanation": f"Matched condition '{condition}' rule: {rule.get('name', 'unnamed')}",
                            "alternatives": [],
                            "confidence": 0.8,
                            "routing_data": routing_data
                        }
                except Exception as e:
                    logger.warning(f"Rule condition evaluation failed: {condition} - {str(e)}")
                    continue
                    
        except Exception as e:
            logger.warning(f"Rule processing error: {str(e)}")
            continue
    
    # Step 3: Fallback to model scoring
    try:
        models = list_models()
        if not models:
            logger.error("No models available for routing")
            return {
                "model_id": SAFE_DEFAULT,
                "rule": "no_models_error",
                "explanation": "No models available in registry",
                "alternatives": [],
                "confidence": 0.0,
                "routing_data": routing_data
            }
        
        # Score and select best models
        top_models = _select_best_models(models, detected_intents, context_tokens, session_id)
        
        if not top_models:
            logger.error("Model scoring failed for all models")
            return {
                "model_id": SAFE_DEFAULT,
                "rule": "scoring_failed",
                "explanation": "All models failed during scoring",
                "alternatives": [],
                "confidence": 0.0,
                "routing_data": routing_data
            }
        
        # Apply confidence threshold logic
        selected_model, selection_reason = _check_confidence_threshold(top_models)
        
        best_model, best_score, best_explanations = top_models[0]
        selected_id = normalize_model_id(selected_model["id"])
        
        # Build alternatives list
        alternatives = [
            {
                "model_id": normalize_model_id(model["id"]),
                "score": score,
                "explanations": explanations[:3]  # Limit for readability
            }
            for model, score, explanations in top_models[1:3]
        ]
        
        # Calculate confidence based on score distribution
        if len(top_models) >= 2:
            score_gap = top_models[0][1] - top_models[1][1] 
            confidence = min(0.95, 0.5 + (score_gap / 10.0))
        else:
            confidence = 0.7
        
        explanation = f"Scored selection: {selected_id} (score={best_score:.1f}, {selection_reason}) - " + \
                     f"Top factors: {', '.join(best_explanations[:3])}"
        
        routing_data.update({
            'selection_method': 'scored_selection',
            'selection_reason': selection_reason,
            'top_score': best_score,
            'score_explanations': best_explanations,
            'alternatives_count': len(alternatives)
        })
        
        logger.info(f"Selected model={selected_id} score={best_score:.1f} confidence={confidence:.2f}")
        
        return {
            "model_id": selected_id,
            "rule": "scored_selection",
            "explanation": explanation,
            "alternatives": alternatives,
            "confidence": confidence,
            "routing_data": routing_data
        }
        
    except Exception as e:
        logger.error("Error during enhanced model scoring: %s", str(e))
        return {
            "model_id": SAFE_DEFAULT,
            "rule": "scoring_error",
            "explanation": f"Error during model scoring: {str(e)}",
            "alternatives": [],
            "confidence": 0.0,
            "routing_data": routing_data
        }
    
    # Final fallback
    logger.warning("All routing methods failed, using safe default")
    return {
        "model_id": SAFE_DEFAULT,
        "rule": "ultimate_fallback",
        "explanation": "All routing methods failed, using safe default model",
        "alternatives": [],
        "confidence": 0.1,
        "routing_data": routing_data
    }


# Backward compatibility function
async def route_model_with_parallel_fallback(message: str, context_tokens: int, 
                                           session_id: Optional[str] = None,
                                           intents: Optional[Set[str]] = None) -> Dict[str, Any]:
    """Async wrapper for route_model for backward compatibility.
    
    In the lightweight system, we don't need actual parallel processing,
    but this maintains the same interface for existing code.
    """
    return route_model(message, context_tokens, intents=intents, session_id=session_id)
