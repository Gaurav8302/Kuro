"""Enhanced Model router with hybrid intent detection and intelligent routing.

Features:
- Hybrid intent detection (regex + embeddings)
- Latency-aware routing with EMA tracking
- Blended scoring system (no hard tiers)
- Session-aware adaptations
- Explainable routing decisions
- Parallel fallback for critical intents

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
from routing.embedding_similarity import get_embedding_similarity, INTENT_EXAMPLES
from routing.latency_tracker import get_latency_tracker
from routing.session_tracker import get_session_manager
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

SAFE_DEFAULT = normalize_model_id("llama-3.3-70B-versatile")
CRITICAL_INTENTS = {"complex_reasoning", "debugging", "long_context_summary"}
CONFIDENCE_THRESHOLD = 0.5  # If top 2 models differ by less than this, pick faster one

def _hybrid_intent_detection(message: str, existing_intents: Optional[Set[str]] = None) -> Tuple[Set[str], List[str]]:
    """Enhanced intent detection using both regex patterns and embeddings.
    
    Returns:
        Tuple of (detected_intents, explanations)
    """
    detected_intents = set(existing_intents) if existing_intents else set()
    explanations = []
    
    # Get embedding similarity matcher
    embedding_sim = get_embedding_similarity()
    
    # Embedding-based intent detection
    if embedding_sim.model is not None:
        intent_similarities = embedding_sim.get_intent_similarity(message, INTENT_EXAMPLES)
        
        for intent, similarity in intent_similarities:
            if similarity > embedding_sim.similarity_threshold:
                detected_intents.add(intent)
                explanations.append(f"embedding_match:{intent}={similarity:.2f}")
    
    # Fallback to rule-based patterns if no embeddings
    if not detected_intents or embedding_sim.model is None:
        # Simple regex-based intent detection as fallback
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["hello", "hi", "hey", "greetings"]):
            detected_intents.add("casual_chat")
            explanations.append("regex_match:casual_chat")
        
        if any(phrase in message_lower for phrase in ["step by step", "explain", "how does", "why"]):
            detected_intents.add("complex_reasoning")
            explanations.append("regex_match:complex_reasoning")
        
        if any(word in message_lower for word in ["summarize", "summary", "tldr", "main points"]):
            detected_intents.add("long_context_summary")
            explanations.append("regex_match:long_context_summary")
        
        if any(word in message_lower for word in ["story", "creative", "imagine", "brainstorm"]):
            detected_intents.add("high_creativity_generation")
            explanations.append("regex_match:high_creativity_generation")
        
        if any(word in message_lower for word in ["debug", "error", "fix", "bug", "traceback"]):
            detected_intents.add("debugging")
            explanations.append("regex_match:debugging")
    
    # Default to casual_chat if nothing detected
    if not detected_intents:
        detected_intents.add("casual_chat")
        explanations.append("default:casual_chat")
    
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
    max_ctx = int(model.get("max_context_tokens", 0) or 0)
    if max_ctx > 0 and context_tokens > max_ctx:
        score -= 10.0
        explanations.append(f"context_overflow:{context_tokens}>{max_ctx}(-10.0)")
    elif max_ctx > context_tokens * 2:  # Bonus for ample context
        bonus = min(2.0, max_ctx / context_tokens - 1)
        score += bonus
        explanations.append(f"context_bonus:+{bonus:.1f}")
    
    # Latency-aware scoring
    latency_tracker = get_latency_tracker()
    latency_score = latency_tracker.get_latency_score(model["id"])
    if latency_score != 0.5:  # Not default/unknown
        latency_boost = latency_score * 3.0  # Up to +3 for very fast models
        score += latency_boost
        explanations.append(f"latency_boost:+{latency_boost:.1f}")
    
    # Session-based preferences
    if session_id:
        session_manager = get_session_manager()
        session = session_manager.get_session(session_id)
        pref_score = session.get_model_preference_score(model["id"])
        if pref_score != 0.5:  # Not neutral
            pref_boost = (pref_score - 0.5) * 4.0  # -2.0 to +2.0
            score += pref_boost
            explanations.append(f"session_preference:{pref_boost:+.1f}")
    
    # Quality vs speed trade-off
    tier = model.get("quality_tier", "medium")
    if any(intent in intents for intent in ["complex_reasoning", "high_creativity_generation"]):
        if tier == "high":
            score += 3.0
            explanations.append("quality_boost:high_tier(+3.0)")
        elif tier == "medium":
            score += 1.0
            explanations.append("quality_boost:medium_tier(+1.0)")
    
    # Cost efficiency for casual queries
    if intents == {"casual_chat"}:
        cost_penalty = float(model.get("cost_score", 1)) * 0.3
        score -= cost_penalty
        explanations.append(f"cost_penalty:-{cost_penalty:.1f}")
    
    return score, explanations


def _select_best_models(models: List[Dict[str, Any]], intents: Set[str], 
                       context_tokens: int, session_id: Optional[str] = None,
                       top_k: int = 3) -> List[Tuple[Dict[str, Any], float, List[str]]]:
    """Score and rank models, returning top candidates with explanations."""
    scored_models = []
    
    for model in models:
        try:
            score, explanations = _score_model_enhanced(model, intents, context_tokens, session_id)
            scored_models.append((model, score, explanations))
        except Exception as e:
            logger.warning(f"Error scoring model {model.get('id', 'unknown')}: {str(e)}")
            continue
    
    # Sort by score descending
    scored_models.sort(key=lambda x: x[1], reverse=True)
    return scored_models[:top_k]


def _check_confidence_threshold(top_models: List[Tuple[Dict[str, Any], float, List[str]]]) -> Tuple[Dict[str, Any], str]:
    """Apply confidence threshold logic - pick faster model if scores are close."""
    if len(top_models) < 2:
        if top_models:
            return top_models[0][0], "single_candidate"
        else:
            return {"id": SAFE_DEFAULT}, "no_candidates"
    
    best_model, best_score, _ = top_models[0]
    second_model, second_score, _ = top_models[1]
    
    score_diff = best_score - second_score
    
    if score_diff < CONFIDENCE_THRESHOLD:
        # Scores are close, pick based on latency
        latency_tracker = get_latency_tracker()
        best_latency = latency_tracker.get_latency(best_model["id"])
        second_latency = latency_tracker.get_latency(second_model["id"])
        
        if best_latency and second_latency and second_latency < best_latency:
            return second_model, f"latency_preference:diff={score_diff:.2f}"
        elif second_latency and not best_latency:
            return second_model, f"known_latency_preference:diff={score_diff:.2f}"
    
    return best_model, f"clear_winner:diff={score_diff:.2f}"

def route_model(message: str, context_tokens: int, intents: Optional[Set[str]] = None, 
                forced_model: Optional[str] = None, intent: Optional[str] = None,
                session_id: Optional[str] = None) -> Dict[str, Any]:
    """Enhanced model routing with hybrid detection and explainable decisions.
    
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
    
    # Enhanced intent detection
    detected_intents, intent_explanations = _hybrid_intent_detection(message, intents)
    routing_data['detected_intents'] = list(detected_intents)
    routing_data['intent_explanations'] = intent_explanations
    
    # Forced override with validation
    if forced_model:
        forced_norm = normalize_model_id(forced_model)
        if forced_norm != forced_model:
            logger.debug("Normalized forced_model %s -> %s", forced_model, forced_norm)
            
        try:
            model_config = get_model(forced_norm)
            if model_config:
                logger.info(f"Using forced model: {forced_norm}")
                return {
                    "model_id": forced_norm,
                    "rule": "forced_override",
                    "explanation": f"User/system forced model selection: {forced_norm}",
                    "alternatives": [],
                    "confidence": 1.0,
                    "routing_data": routing_data
                }
            else:
                logger.warning("Forced model %s not found, falling back to routing", forced_norm)
        except Exception as e:
            logger.warning("Error validating forced model %s: %s, falling back", forced_norm, str(e))
    
    # Enhanced rule evaluation
    first_intent = sorted(detected_intents)[0] if detected_intents else "casual_chat"
    logger.info(f"Routing query intent={first_intent} session={session_id} message_len={len(message)}")
    
    vars = {"context_tokens": context_tokens, "message_len_chars": len(message)}
    
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
                logger.info(f"Rule match intent={r_intent} -> model={chosen_norm}")
                routing_data['rule_match_type'] = 'intent'
                routing_data['matched_rule'] = rule.get("name", "intent_match")
                
                return {
                    "model_id": chosen_norm,
                    "rule": rule.get("name", "intent_match"),
                    "explanation": f"Rule-based intent match: {r_intent} -> {chosen_norm} (+100 rule boost)",
                    "alternatives": [],
                    "confidence": 0.9,
                    "routing_data": routing_data
                }
            
            # Condition-based matching
            cond = rule.get("condition")
            if cond and _eval_condition_safe(cond, vars):
                logger.info(f"Rule match condition={cond} -> model={chosen_norm}")
                routing_data['rule_match_type'] = 'condition'
                routing_data['matched_rule'] = rule.get("name", "condition_match")
                
                return {
                    "model_id": chosen_norm,
                    "rule": rule.get("name", "condition_match"),
                    "explanation": f"Rule-based condition match: {cond} -> {chosen_norm}",
                    "alternatives": [],
                    "confidence": 0.8,
                    "routing_data": routing_data
                }
                
        except Exception as e:
            logger.warning("Error evaluating rule %s: %s", rule.get("name", "unnamed"), str(e))
            continue
    
    # Enhanced model scoring and selection
    try:
        models = list_models()
        if not models:
            logger.warning("No models available in registry")
            return {
                "model_id": SAFE_DEFAULT,
                "rule": "unavailable_registry",
                "explanation": "No models available in registry",
                "alternatives": [],
                "confidence": 0.0,
                "routing_data": routing_data
            }
        
        logger.debug("Scoring %d available models", len(models))
        
        # Get top candidates with detailed scoring
        top_models = _select_best_models(models, detected_intents, context_tokens, session_id, top_k=3)
        
        if not top_models:
            logger.warning("No models scored positively")
            return {
                "model_id": SAFE_DEFAULT,
                "rule": "no_positive_scores",
                "explanation": "No models achieved positive scores",
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


def _eval_condition_safe(expr: str, vars: Dict[str, Any]) -> bool:
    """Safe expression evaluator for rule conditions."""
    try:
        # Only allow safe variable names
        allowed_names = {"context_tokens", "message_len_chars"}
        return bool(eval(expr, {"__builtins__": {}}, {k: v for k, v in vars.items() if k in allowed_names}))
    except Exception:
        return False


# Parallel fallback routing for critical intents
async def route_model_with_parallel_fallback(message: str, context_tokens: int, 
                                          intents: Optional[Set[str]] = None,
                                          session_id: Optional[str] = None) -> Dict[str, Any]:
    """Route with parallel fallback for critical intents."""
    detected_intents, _ = _hybrid_intent_detection(message, intents)
    
    # Check if this requires parallel fallback
    is_critical = bool(detected_intents.intersection(CRITICAL_INTENTS))
    
    if not is_critical:
        # Standard routing for non-critical intents
        return route_model(message, context_tokens, detected_intents, session_id=session_id)
    
    # Get primary routing result
    primary_result = route_model(message, context_tokens, detected_intents, session_id=session_id)
    
    # For critical intents, also get backup options ready
    alternatives = primary_result.get('alternatives', [])
    if alternatives:
        fallback_models = [alt['model_id'] for alt in alternatives[:2]]
        primary_result['fallback_ready'] = fallback_models
        logger.info(f"Critical intent detected, fallbacks ready: {fallback_models}")
    
    return primary_result

__all__ = ["route_model", "route_model_with_parallel_fallback"]
