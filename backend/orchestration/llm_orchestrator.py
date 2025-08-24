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

# Simple in-process cache for last successful model per intent for a session
_last_model_by_intent: Dict[str, Dict[str, str]] = {}

def _get_session_key(session_id: Optional[str]) -> str:
    return session_id or "anon"

def _remember_model(session_id: Optional[str], intent: Optional[str], model_id: str) -> None:
    if not intent:
        return
    sk = _get_session_key(session_id)
    _last_model_by_intent.setdefault(sk, {})[intent] = model_id

def _recall_model(session_id: Optional[str], intent: Optional[str]) -> Optional[str]:
    if not intent:
        return None
    return _last_model_by_intent.get(_get_session_key(session_id), {}).get(intent)

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
    # Router thresholds and weighted confidence
    RULE_MIN = 0.75
    LLM_MIN = 0.65
    try:
        v2 = await get_best_model_v2(user_message)
        model_id = v2["chosen_model"]
        selection_reason = v2.get("reason")
        cache_hit = selection_reason == "cache_hit"
        router_conf = float(v2.get("confidence", 0.6))
    except Exception:
        routing = route_model(user_message, ctx_tokens, intents=intents, forced_model=developer_forced_model)
        model_id = routing["model_id"]
        selection_reason = routing.get("rule")
        router_conf = 0.6
    fallbacks: List[str] = []
    attempts = 0
    last_error: Optional[Exception] = None
    reply: Optional[str] = None
    # Try to reuse last successful model for this primary intent within session
    primary_intent = next(iter(intents)) if intents else None
    sticky = _recall_model(None, primary_intent)
    if sticky:
        model_id = sticky

    # Exponential backoff helper
    import random
    def _backoff(i: int) -> float:
        return min(2 ** i + random.random(), 8.0)

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
            # Retry transient errors with backoff
            retries = 0
            while True:
                try:
                    reply = client.generate_content(
                        prompt=user_message,
                        system_instruction=full_system,
                        intent=primary_intent,
                        model_id=model_id,
                    )
                    break
                except Exception as e_inner:
                    msg = str(e_inner)
                    transient = any(k in msg for k in ("timeout", "429", "temporar", "Retry after", "rate"))
                    if not transient or retries >= 2:
                        raise
                    time.sleep(_backoff(retries))
                    retries += 1
            record_success(model_id)
            _remember_model(None, primary_intent, model_id)
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
        via = ("rule" if selection_reason and "rule:" in selection_reason else "router")
        observe_routing(latency_ms, used_fallback=bool(fallbacks), via=via, cache_hit=cache_hit)
    except Exception:
        pass

    # Structured JSON logging to file for offline analysis
    try:
        from config.model_config import get_model_source
        log_obj = {
            "query": user_message[:500],
            "chosen_model": model_id,
            "source": get_model_source(model_id or ""),
            "reason": selection_reason,
            "confidence": router_conf,
            "fallback_used": bool(fallbacks),
            "latency_ms": latency_ms,
        }
        _write_jsonl(log_obj)
    except Exception:
        pass
    return result

__all__ = ["orchestrate"]
