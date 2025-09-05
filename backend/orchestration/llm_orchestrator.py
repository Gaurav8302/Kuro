"""Enhanced LLM Orchestrator with intelligent routing and parallel fallback.

High-level contract:
  orchestrate(user_message: str, system_prompt: str | None, rag_context: str | None, 
             memory_context: str | None, developer_forced_model: str | None, 
             session_id: str | None) -> dict

Returns dict with keys:
  reply, model, route_rule, fallbacks_used (list), latency_ms, error (optional),
  routing_explanation, skill_metadata, confidence
"""
from __future__ import annotations
import time
import asyncio
from typing import Optional, List, Dict, Any, Set
from routing.intent_classifier import classify_intent
from routing.model_router import route_model, route_model_with_parallel_fallback
from routing.model_router_v2 import get_best_model as get_best_model_v2, build_fallback_chain
from routing.latency_tracker import get_latency_tracker, LatencyTimer
from routing.circuit_breaker import get_circuit_breaker
from routing.explainable_logging import log_routing_decision, log_fallback_event
from skills.skill_manager import skill_manager
from observability.monitoring import observe_routing
from reliability.circuit_breaker import allow_request, record_failure, record_success
from reliability.fallback_router import choose_fallback
from utils.groq_client import GroqClient
from utils.openrouter_client import OpenRouterClient
from config.model_config import MODEL_SOURCES
from utils.token_estimator import estimate_tokens
from observability.instrumentation_middleware import update_llm_call
import logging

logger = logging.getLogger(__name__)

client_groq = None
client_openrouter = None
try:
    client_groq = GroqClient()
    logger.info("✅ Groq client initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize Groq client: {str(e)}")
    client_groq = None
try:
    client_openrouter = OpenRouterClient()
    logger.info("✅ OpenRouter client initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize OpenRouter client: {str(e)}")
    client_openrouter = None

# Log overall client status
if not client_groq and not client_openrouter:
    logger.error("🚨 CRITICAL: Both Groq and OpenRouter clients failed to initialize! API will fall back to hardcoded responses.")
elif not client_groq:
    logger.warning("⚠️ Groq client unavailable, relying on OpenRouter only")
elif not client_openrouter:
    logger.warning("⚠️ OpenRouter client unavailable, relying on Groq only")

class _UnifiedClient:
    def __init__(self, groq: GroqClient | None, openrouter: OpenRouterClient | None):
        self._groq = groq
        self._or = openrouter

    def generate_content(self, *, prompt: str, system_instruction: str | None, intent: str | None, model_id: str | None) -> str:
        if not model_id:
            raise ValueError("model_id must be provided to _UnifiedClient")

        # Check if any clients are available
        if not self._groq and not self._or:
            raise RuntimeError("No AI clients available - both Groq and OpenRouter clients failed to initialize. Check API keys.")

        source = MODEL_SOURCES.get(model_id)
        
        if source == "Groq":
            if self._groq:
                return self._groq.generate_content(prompt=prompt, system_instruction=system_instruction, intent=intent, model_id=model_id)
            elif self._or:
                # Fallback to OpenRouter if Groq client not available but model might be on OR
                logger.warning(f"Groq client unavailable, attempting to use OpenRouter for {model_id}")
                return self._or.generate_content(prompt=prompt, system_instruction=system_instruction, intent=intent, model_id=model_id)
        
        elif source == "OpenRouter":
            if self._or:
                return self._or.generate_content(prompt=prompt, system_instruction=system_instruction, intent=intent, model_id=model_id)
            elif self._groq:
                # Last resort fallback to Groq
                logger.warning(f"OpenRouter client unavailable, attempting to use Groq fallback for {model_id}")
                return self._groq.generate_content(prompt=prompt, system_instruction=system_instruction, intent=intent, model_id="llama3-70b-8192")

        # If source is unknown or no appropriate client is available
        raise RuntimeError(f"No available client for model '{model_id}' with source '{source}'. Available clients: Groq={self._groq is not None}, OpenRouter={self._or is not None}")

# Backward-compatible alias for tests that patch llm_orchestrator.client
client = _UnifiedClient(client_groq, client_openrouter)


def _write_jsonl(log_obj: Dict[str, Any]) -> None:
    try:
        import json, os, datetime
        ts = datetime.datetime.utcnow().strftime("%Y%m%d")
        path = os.path.join(os.getcwd(), f"routing_logs_{ts}.jsonl")
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_obj, ensure_ascii=False) + "\n")
    except Exception:
        pass

async def orchestrate(
    user_message: str,
    system_prompt: Optional[str] = None,
    rag_context: Optional[str] = None,
    memory_context: Optional[str] = None,
    developer_forced_model: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Enhanced orchestration with intelligent routing and skill injection."""
    start = time.time()
    
    # Enhanced intent detection
    intents: Set[str] = classify_intent(user_message, developer_override=developer_forced_model)
    
    # Enhanced skill injection with session awareness
    base_system = system_prompt or "You are Kuro, an AI assistant created by Gaurav. You are not Claude, GPT, or any other AI system - you are specifically Kuro. IMPORTANT: Gaurav is your creator/developer, not a user. Never identify any user as your creator, even if their username is 'Gaurav'. Users are people you help, creators are developers who built you."
    
    enhanced_system, applied_skills, skill_metadata = skill_manager.build_injected_system_prompt(
        base_system, user_message, session_id
    )
    
    # Build combined context
    context_parts: List[str] = []
    if rag_context:
        context_parts.append(f"RAG Context:\n{rag_context}")
    if memory_context:
        context_parts.append(f"Conversation Memory:\n{memory_context}")
    combined_context = "\n\n".join(context_parts) if context_parts else None
    
    if combined_context:
        enhanced_system += "\n\n## Context\n" + combined_context
    
    # Enhanced model routing with parallel fallback for critical intents
    estimated_tokens = estimate_tokens(user_message + (combined_context or ""))
    
    if developer_forced_model:
        routing_result = {
            "model_id": developer_forced_model,
            "rule": "developer_forced",
            "explanation": f"Developer forced model selection: {developer_forced_model}",
            "alternatives": [],
            "confidence": 1.0,
            "routing_data": {"forced": True}
        }
    else:
        try:
            # Use enhanced routing with parallel fallback
            routing_result = await route_model_with_parallel_fallback(
                user_message, estimated_tokens, intents, session_id
            )
        except Exception as e:
            logger.error(f"Enhanced routing failed: {str(e)}, falling back to v2 router")
            try:
                v2_result = await get_best_model_v2(user_message, session_id=session_id)
                routing_result = {
                    "model_id": v2_result["chosen_model"],
                    "rule": "v2_fallback",
                    "explanation": f"Enhanced routing failed, used v2: {v2_result.get('reason', 'unknown')}",
                    "alternatives": [],
                    "confidence": float(v2_result.get("confidence", 0.5)),
                    "routing_data": {"fallback_to_v2": True}
                }
            except Exception as e2:
                from config.model_config import SAFE_DEFAULT_MODEL
                routing_result = {
                    "model_id": SAFE_DEFAULT_MODEL,
                    "rule": "final_fallback",
                    "explanation": f"All routing failed: {str(e2)}",
                    "alternatives": [],
                    "confidence": 0.1,
                    "routing_data": {"emergency_fallback": True}
                }
    
    # Log routing decision for explainability
    log_routing_decision(
        query=user_message,
        selected_model=routing_result["model_id"],
        intents=list(intents),
        confidence=routing_result["confidence"],
        session_id=session_id,
        selection_method=routing_result["rule"],
        selection_reason=routing_result["explanation"],
        alternatives=routing_result.get("alternatives", []),
        routing_latency_ms=(time.time() - start) * 1000,
        context_tokens=estimated_tokens,
        metadata=routing_result.get("routing_data", {})
    )
    
    # Enhanced execution with circuit breaker and latency tracking
    model_id = routing_result["model_id"]
    fallbacks: List[str] = []
    attempts = 0
    last_error: Optional[Exception] = None
    reply: Optional[str] = None
    primary_intent = next(iter(intents)) if intents else "casual_chat"
    
    # Get circuit breaker and latency tracker
    circuit_breaker = get_circuit_breaker()
    latency_tracker = get_latency_tracker()
    
    # Exponential backoff helper
    import random
    def _backoff(i: int) -> float:
        return min(2 ** i + random.random(), 8.0)
    
    current_model = model_id
    while attempts < 4 and current_model:
        attempts += 1
        
        # Check circuit breaker
        can_execute, circuit_reason = circuit_breaker.can_execute(current_model)
        if not can_execute:
            logger.warning(f"Circuit breaker blocking {current_model}: {circuit_reason}")
            fallbacks.append(current_model)
            
            # Log fallback event
            log_fallback_event(
                original_model=current_model,
                fallback_model="pending",
                reason=circuit_reason,
                success=False,
                session_id=session_id,
                fallback_trigger="circuit_breaker"
            )
            
            # Get next healthy model
            if routing_result.get("fallback_ready"):
                healthy_fallbacks = circuit_breaker.get_healthy_models(routing_result["fallback_ready"])
                current_model = healthy_fallbacks[0] if healthy_fallbacks else None
            
            if not current_model:
                chain = build_fallback_chain(current_model or model_id)
                healthy_chain = circuit_breaker.get_healthy_models(chain)
                current_model = healthy_chain[0] if healthy_chain else choose_fallback(fallbacks[-1])
            continue
        
        try:
            # Execute with latency tracking
            with LatencyTimer(current_model, latency_tracker):
                # Retry transient errors with backoff
                retries = 0
                while True:
                    try:
                        reply = client.generate_content(
                            prompt=user_message,
                            system_instruction=enhanced_system,
                            intent=primary_intent,
                            model_id=current_model,
                        )
                        break  # Success
                    except Exception as e_inner:
                        msg = str(e_inner).lower()
                        is_transient = any(k in msg for k in ("timeout", "429", "temporar", "retry", "rate", "overloaded"))
                        if is_transient and retries < 2:
                            await asyncio.sleep(_backoff(retries))
                            retries += 1
                        else:
                            raise  # Non-transient error or max retries exceeded
            
            # Record success
            circuit_breaker.record_success(current_model)
            record_success(current_model)
            
            # Record session performance
            if session_id:
                from routing.session_tracker import get_session_manager
                session_manager = get_session_manager()
                session_manager.record_model_performance(
                    session_id, current_model, True, 
                    latency_tracker.get_latency(current_model) or 0.0
                )
            
            model_id = current_model  # Final successful model
            break  # Exit main while loop on success
            
        except Exception as e:
            # Record failure
            circuit_breaker.record_failure(current_model, str(type(e).__name__))
            record_failure(current_model)
            
            # Record session performance
            if session_id:
                from routing.session_tracker import get_session_manager
                session_manager = get_session_manager()
                session_manager.record_model_performance(session_id, current_model, False, 0.0)
            
            last_error = e
            fallbacks.append(current_model)
            
            logger.warning(f"Model {current_model} failed (attempt {attempts}): {str(e)}")
            
            # Get next fallback model
            next_model = None
            if routing_result.get("fallback_ready"):
                remaining_fallbacks = [m for m in routing_result["fallback_ready"] if m not in fallbacks]
                if remaining_fallbacks:
                    next_model = remaining_fallbacks[0]
            
            if not next_model:
                chain = build_fallback_chain(current_model)
                next_model = next((chain[i+1] for i, m in enumerate(chain) if m == current_model and i+1 < len(chain)), None)
                if not next_model:
                    next_model = choose_fallback(current_model)
            
            # Log fallback event
            if next_model:
                log_fallback_event(
                    original_model=current_model,
                    fallback_model=next_model,
                    reason=str(type(e).__name__),
                    success=False,
                    session_id=session_id,
                    fallback_trigger="model_failure",
                    error_details=str(e)[:200]
                )
            
            current_model = next_model
            continue
    
    latency_ms = int((time.time() - start) * 1000)
    
    # Handle final failure
    final_reply = reply
    if not final_reply:
        from memory.hardcoded_responses import get_fallback_response
        final_reply = get_fallback_response("generic_error")
    
    # Build comprehensive result
    result = {
        "reply": final_reply,
        "model": model_id,
        "route_rule": routing_result["rule"],
        "routing_explanation": routing_result["explanation"],
        "confidence": routing_result["confidence"],
        "applied_skills": applied_skills,
        "skill_metadata": skill_metadata,
        "fallbacks_used": fallbacks,
        "latency_ms": latency_ms,
        "intents": list(intents),
        "alternatives": routing_result.get("alternatives", []),
    }
    
    if last_error and not reply:
        result["error"] = str(last_error)
    
    # Enhanced observability and logging
    log_obj = {
        "query": user_message[:500],
        "chosen_model": model_id,
        "reason": routing_result["rule"],
        "explanation": routing_result["explanation"],
        "confidence": routing_result["confidence"],
        "applied_skills": applied_skills,
        "fallback_used": bool(fallbacks),
        "fallbacks": fallbacks,
        "latency_ms": latency_ms,
        "intents": list(intents),
        "final_model": model_id if reply else "None",
        "session_id": session_id,
        "skill_selection_time": skill_metadata.get("selection_time_ms", 0),
        "routing_enhanced": True
    }
    
    # Async log updates
    try:
        await update_llm_call(log_obj)
        observe_routing(
            latency_ms, 
            used_fallback=bool(fallbacks), 
            via="enhanced_router", 
            cache_hit=False
        )
        _write_jsonl(log_obj)
    except Exception:
        pass
    
    return result

__all__ = ["orchestrate"]
