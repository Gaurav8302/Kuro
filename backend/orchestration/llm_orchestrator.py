"""LLM Orchestrator: multi-model routing, execution, fallback, logging.

High-level contract:
  orchestrate(user_message: str, system_prompt: str | None, rag_context: str | None, memory_context: str | None, developer_forced_model: str | None) -> dict

Returns dict with keys:
  reply, model, route_rule, fallbacks_used (list), latency_ms, error (optional)
"""
from __future__ import annotations
import time
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

client_groq = None
client_openrouter = None
try:
    client_groq = GroqClient()
except Exception:
    client_groq = None
try:
    client_openrouter = OpenRouterClient()
except Exception:
    client_openrouter = None

class _UnifiedClient:
    def __init__(self, groq: GroqClient | None, openrouter: OpenRouterClient | None):
        self._groq = groq
        self._or = openrouter
    def generate_content(self, *, prompt: str, system_instruction: str | None, intent: str | None, model_id: str | None) -> str:
        source = MODEL_SOURCES.get(model_id or "", "OpenRouter")
        # Skip to available provider transparently
        if source == "OpenRouter":
            if self._or:
                return self._or.generate_content(prompt=prompt, system_instruction=system_instruction, intent=intent, model_id=model_id)
            if self._groq:
                return self._groq.generate_content(prompt=prompt, system_instruction=system_instruction, intent=intent, model_id=model_id)
            raise RuntimeError("No provider client available")
        else:  # Groq
            if self._groq:
                return self._groq.generate_content(prompt=prompt, system_instruction=system_instruction, intent=intent, model_id=model_id)
            if self._or:
                return self._or.generate_content(prompt=prompt, system_instruction=system_instruction, intent=intent, model_id=model_id)
            raise RuntimeError("No provider client available")

# Backward-compatible alias for tests that patch llm_orchestrator.client
client = _UnifiedClient(client_groq, client_openrouter)

async def orchestrate(
    user_message: str,
    system_prompt: Optional[str] = None,
    rag_context: Optional[str] = None,
    memory_context: Optional[str] = None,
    developer_forced_model: Optional[str] = None,
) -> Dict[str, Any]:
    start = time.time()
    intents: Set[str] = classify_intent(user_message)
    # Build combined prompt fragments
    context_parts: List[str] = []
    if rag_context:
        context_parts.append(f"RAG:\n{rag_context}")
    if memory_context:
        context_parts.append(f"MEMORY:\n{memory_context}")
    combined_context = "\n\n".join(context_parts) if context_parts else None
    # Rough context token est
    ctx_tokens = estimate_tokens((combined_context or "") + user_message)
    # New hybrid router (fast, with 5s cap). Falls back to legacy if needed.
    selection_reason = None
    cache_hit = False
    try:
        v2 = await get_best_model_v2(user_message)
        model_id = v2["chosen_model"]
        selection_reason = v2.get("reason")
        cache_hit = selection_reason == "cache_hit"
    except Exception:
        routing = route_model(user_message, ctx_tokens, intents=intents, forced_model=developer_forced_model)
        model_id = routing["model_id"]
        selection_reason = routing.get("rule")
    fallbacks: List[str] = []
    attempts = 0
    last_error: Optional[Exception] = None
    reply: Optional[str] = None
    while attempts < 4 and model_id:
        attempts += 1
        if not allow_request(model_id):
            fallbacks.append(model_id)
            # Prefer explicit chain from v2 if available
            chain = build_fallback_chain(model_id)
            nxt = None
            if model_id in chain:
                idx = chain.index(model_id)
                nxt = chain[idx+1] if idx+1 < len(chain) else None
            model_id = nxt or choose_fallback(model_id)
            continue
        try:
            full_system = system_prompt or "You are Kuro, a helpful AI assistant."
            if combined_context:
                full_system += "\n\nContext:\n" + combined_context
            reply = client.generate_content(
                prompt=user_message,
                system_instruction=full_system,
                intent=next(iter(intents)) if intents else None,
                model_id=model_id,
            )
            record_success(model_id)
            break
        except Exception as e:
            record_failure(model_id)
            last_error = e
            fallbacks.append(model_id)
            chain = build_fallback_chain(model_id)
            nxt = None
            if model_id in chain:
                idx = chain.index(model_id)
                nxt = chain[idx+1] if idx+1 < len(chain) else None
            model_id = nxt or choose_fallback(model_id)
            continue
    latency_ms = int((time.time() - start) * 1000)
    result = {
        "reply": reply or "I'm sorry, I'm temporarily unavailable. Please try again soon.",
        "model": model_id,
    "route_rule": selection_reason,
        "fallbacks_used": fallbacks,
        "latency_ms": latency_ms,
        "intents": list(intents),
    }
    if last_error and not reply:
        result["error"] = str(last_error)
    # Async log update
    try:
        await update_llm_call({
            "model_selected": model_id,
            "routing_reason": selection_reason,
            "intents": list(intents),
            "fallback_chain": fallbacks,
            "total_latency_ms": latency_ms,
        })
    except Exception:
        pass
    try:
        observe_routing(latency_ms, used_fallback=bool(fallbacks), via=("rule" if selection_reason and "rule:" in selection_reason else "router"), cache_hit=cache_hit)
    except Exception:
        pass
    return result

__all__ = ["orchestrate"]
