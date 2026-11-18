import json
import re
from typing import Dict, Any, List

RECALL_PATTERNS = [
    re.compile(r"\blast\s+time\b", re.IGNORECASE),
    re.compile(r"\bprevious(ly|\s+session|\s+conversation)?\b", re.IGNORECASE),
    re.compile(r"\bremember\b", re.IGNORECASE),
    re.compile(r"\bwe\s+talked\s+about\b", re.IGNORECASE),
    re.compile(r"\bwhen\s+we\s+(talked|discussed|spoke|chatted|mentioned)\b", re.IGNORECASE),
    re.compile(r"\bdo\s+you\s+(know|remember|recall)\b", re.IGNORECASE),
    re.compile(r"\brecall\b", re.IGNORECASE),
    re.compile(r"\bearlier\b", re.IGNORECASE),
    re.compile(r"\bpast\s+(conversation|session|chat)\b", re.IGNORECASE),
    re.compile(r"\bbefore\s+we\b", re.IGNORECASE),
    re.compile(r"\bwhat\s+did\s+(we|i|you)\s+(talk|discuss|say|mention)\b", re.IGNORECASE),
    re.compile(r"\bi\s+(told|mentioned|said)\s+(you|that)\b", re.IGNORECASE),
    re.compile(r"\byou\s+(said|told|mentioned)\b", re.IGNORECASE),
    re.compile(r"\bwhat\s+do\s+you\s+know\s+about\s+me\b", re.IGNORECASE),
    re.compile(r"\beverything\s+you\s+know\s+about\s+me\b", re.IGNORECASE),
    re.compile(r"\b(summary|recap)\s+of\s+(everything|our\s+past|what\s+you\s+know)\b", re.IGNORECASE),
    re.compile(r"\b(what|which|where|when|who)\s+.*(schedule|routine|plan|plans|goal|goals|book|role|gear|camera|language|framework|marathon|training|vacation|trip|dog|pet|hobby)\b", re.IGNORECASE),
    re.compile(r"\bmy\s+(name|trip|vacation|travel|plan|plans|goal|goals|project|job|work|stack|language|favorite|preference|preferences|routine|schedule|training|marathon|fitness|diet|book|reading|pet|dog|cat|gear|camera|destination)\b", re.IGNORECASE),
    re.compile(r"\bwhere\s+(and\s+when\s+)?am\s+i\s+(traveling|going|visiting)\b", re.IGNORECASE),
    re.compile(r"\bwhat\s+(am\s+i|was\s+i|do\s+i)\s+(reading|doing|planning|packing|training|using|building)\b", re.IGNORECASE),
    re.compile(r"\bwho\s+am\s+i\b", re.IGNORECASE),
    re.compile(r"\bcontinue\s+(where\s+we\s+left\s+off|our\s+work|from\s+before)\b", re.IGNORECASE),
]

DOC_PATTERNS = [
    re.compile(r"\b(document|pdf|file|notes|doc|upload|uploaded|report)\b", re.IGNORECASE),
]


class MemoryController:
    def __init__(self, llm_client=None):
        self.llm = llm_client

    async def decide(self, intent_data: dict, user_input: str = "") -> dict:
        """
        Dynamically decide whether to trigger memory retrieval based on intent and user input.
        Returns:
        {
            "use_memory": bool,
            "types": list,
            "top_k": int
        }
        """
        default = {"use_memory": False, "types": [], "top_k": 0}
        clean_input = (user_input or "").strip()

        # 1. Fast deterministic check: Explicit memory recall triggers
        if any(pat.search(clean_input) for pat in RECALL_PATTERNS):
            types = ["fact", "preference", "event", "session_summary"]
            if any(pat.search(clean_input) for pat in DOC_PATTERNS):
                types.append("document_chunk")
            return {"use_memory": True, "types": types, "top_k": 5}

        # 2. Check intent signals from intent_data
        intent = str(intent_data.get("intent", "general")).lower()
        needs_memory = bool(intent_data.get("needs_memory", False))
        raw_types = intent_data.get("memory_types", [])

        if intent in ["personal", "project", "learning"] or needs_memory:
            types = ["fact", "preference", "event", "session_summary"]
            if raw_types:
                for t in raw_types:
                    ts = str(t).lower().strip()
                    if ts.endswith("s"):
                        ts = ts[:-1]
                    if ts not in types:
                        types.append(ts)
            return {"use_memory": True, "types": types, "top_k": 5}

        # 3. For casual/short chit-chat, skip retrieval to save latency
        words = clean_input.split()
        casual_greetings = {"hi", "hello", "hey", "sup", "yo", "thanks", "thank", "ok", "okay", "cool", "bye", "goodbye", "gm", "gn"}
        if intent == "casual" or (len(words) <= 2 and any(w.lower() in casual_greetings for w in words)):
            return default

        # 4. Transparent semantic probing for all substantive queries (ChatGPT style)
        types = ["fact", "preference", "event", "session_summary"]
        if any(pat.search(clean_input) for pat in DOC_PATTERNS):
            types.append("document_chunk")
        return {"use_memory": True, "types": types, "top_k": 4}

    def _validate_decision(self, decision):
        if not isinstance(decision, dict):
            return None

        use_memory = bool(decision.get("use_memory", False))
        raw_types = decision.get("types", [])
        if not isinstance(raw_types, list):
            raw_types = []

        normalized = []
        for t in raw_types:
            if not isinstance(t, str):
                continue
            ts = t.strip().lower()
            if ts in ("fact", "facts"):
                normalized.append("fact")
            elif ts in ("preference", "preferences"):
                normalized.append("preference")
            elif ts in ("event", "events"):
                normalized.append("event")
            elif ts in ("session_summary", "session_summaries", "summary", "summaries"):
                normalized.append("session_summary")
            elif ts in ("document_chunk", "document", "doc"):
                normalized.append("document_chunk")

        try:
            top_k = int(decision.get("top_k", 0))
        except Exception:
            top_k = 0
        top_k = max(0, min(top_k, 10))

        if not use_memory:
            return {"use_memory": False, "types": [], "top_k": 0}

        normalized = list(dict.fromkeys(normalized))
        if not normalized:
            normalized = ["fact", "preference", "session_summary"]

        return {
            "use_memory": True,
            "types": normalized,
            "top_k": max(top_k, 1),
        }
