"""LLM Orchestrator: multi-model routing, execution, fallback, logging.

High-level contract:
  orchestrate(user_message: str, system_prompt: str | None, rag_context: str | None, memory_context: str | None, developer_forced_model: str | None) -> dict

Returns dict with keys:
  reply, model, route_rule, fallbacks_used (list), latency_ms, error (optional)
"""
from __future__ import annotations
import time
import asyncio
from typing import Optional, List, Dict, Any, Set
from routing.intent_classifier import classify_intent
from routing.model_router import route_model
from routing.model_router_v2 import get_best_model as get_best_model_v2, build_fallback_chain
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
    start = time.time()
    intents: Set[str] = classify_intent(user_message, developer_override=developer_forced_model)
    
    # Build combined prompt fragments
    context_parts: List[str] = []
    if rag_context:
        context_parts.append(f"RAG Context:\n{rag_context}")
    if memory_context:
        context_parts.append(f"Conversation Memory:\n{memory_context}")
    combined_context = "\n\n".join(context_parts) if context_parts else None

    # --- Model Routing ---
    selection_reason = "unknown"
    router_conf = 0.5
    model_id = None
    
    if developer_forced_model:
        model_id = developer_forced_model
        selection_reason = "developer_forced"
        router_conf = 1.0
    else:
        try:
            # Use the advanced v2 router as the primary choice
            v2_result = await get_best_model_v2(user_message, session_id=session_id)
            model_id = v2_result["chosen_model"]
            selection_reason = v2_result.get("reason", "v2_router")
            router_conf = float(v2_result.get("confidence", 0.5))
        except Exception as e:
            # If v2 router fails, fall back to a safe, high-quality default
            from config.model_config import SAFE_DEFAULT_MODEL
            model_id = SAFE_DEFAULT_MODEL
            selection_reason = f"router_exception_fallback:{e}"
            router_conf = 0.1

    fallbacks: List[str] = []
    attempts = 0
    last_error: Optional[Exception] = None
    reply: Optional[str] = None
    primary_intent = next(iter(intents)) if intents else "casual_chat"

    # Exponential backoff helper
    import random
    def _backoff(i: int) -> float:
        return min(2 ** i + random.random(), 8.0)

    current_model = model_id
    while attempts < 4 and current_model:
        attempts += 1
        if not allow_request(current_model):
            fallbacks.append(current_model)
            chain = build_fallback_chain(current_model)
            # Get next model in the predefined chain
            current_model = next((chain[i+1] for i, m in enumerate(chain) if m == current_model and i+1 < len(chain)), None)
            # If no more models in chain, use the generic fallback router
            if not current_model:
                current_model = choose_fallback(fallbacks[-1])
            continue
        
        try:
            full_system = system_prompt or "You are Kuro, an AI assistant created by Gaurav. You are not Claude, GPT, or any other AI system - you are specifically Kuro."
            if combined_context:
                full_system += "\n\n## Context\n" + combined_context
            
            # Retry transient errors (e.g., rate limits, timeouts) with backoff
            retries = 0
            while True:
                try:
                    reply = client.generate_content(
                        prompt=user_message,
                        system_instruction=full_system,
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
            
            record_success(current_model)
            model_id = current_model # Final successful model
            break # Exit main while loop on success

        except Exception as e:
            record_failure(current_model)
            last_error = e
            fallbacks.append(current_model)
            
            # Use fallback chain for next attempt
            chain = build_fallback_chain(current_model)
            current_model = next((chain[i+1] for i, m in enumerate(chain) if m == current_model and i+1 < len(chain)), None)
            if not current_model:
                current_model = choose_fallback(fallbacks[-1])
            continue

    latency_ms = int((time.time() - start) * 1000)
    
    final_reply = reply
    if not final_reply:
        from memory.hardcoded_responses import get_fallback_response
        final_reply = get_fallback_response("generic_error")

    result = {
        "reply": final_reply,
        "model": model_id,
        "route_rule": selection_reason,
        "fallbacks_used": fallbacks,
        "latency_ms": latency_ms,
        "intents": list(intents),
    }
    if last_error and not reply:
        result["error"] = str(last_error)

    # --- Observability & Logging ---
    log_obj = {
        "query": user_message[:500],
        "chosen_model": model_id,
        "reason": selection_reason,
        "confidence": router_conf,
        "fallback_used": bool(fallbacks),
        "fallbacks": fallbacks,
        "latency_ms": latency_ms,
        "intents": list(intents),
        "final_model": model_id if reply else "None",
    }
    
    # Async log updates
    try:
        await update_llm_call(log_obj)
        observe_routing(latency_ms, used_fallback=bool(fallbacks), via="v2_router", cache_hit=(selection_reason == "cache_hit"))
        _write_jsonl(log_obj)
    except Exception:
        pass
        
    return result

__all__ = ["orchestrate"]
