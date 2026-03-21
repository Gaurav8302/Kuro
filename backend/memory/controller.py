import json

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

        # If we have an LLM driven controller, we can formulate a prompt
        if self.llm and user_input:
            prompt = f"""
            Analyze the user input and decide memory retrieval strategy.
            User input: "{user_input}"
            Detected intent: "{intent_data.get('intent', 'general')}"
            
            Return JSON only:
            {{
                "use_memory": true/false,
                "types": ["facts", "preferences", "events"], 
                "top_k": int (0-10)
            }}
            """
            
            try:
                response = await self.llm.generate(prompt) # Assuming generate logic exists in llm
                text = response.strip()
                if text.startswith("```json"): text = text.replace("```json", "", 1)
                if text.startswith("```"): text = text.replace("```", "", 1)
                if text.endswith("```"): text = text[:-3]
                
                decision = json.loads(text.strip())
                validated = self._validate_decision(decision)
                if validated is not None:
                    return validated
            except Exception:
                pass # Fallback to rule-based

        # Fallback to rule logic, taking the previous logic and enhancing it
        if not intent_data.get("needs_memory"):
            return default

        intent = intent_data.get("intent", "general")

        # dynamic rules
        if intent in ["personal", "project", "learning"]:
            return {"use_memory": True, "types": ["facts", "preferences", "events"], "top_k": 10}

        if intent == "casual":
            return default

        types = intent_data.get("memory_types", [])
        fallback = {
            "use_memory": bool(types), 
            "types": types, 
            "top_k": 5
        }
        return self._validate_decision(fallback) or default

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

        try:
            top_k = int(decision.get("top_k", 0))
        except Exception:
            top_k = 0
        top_k = max(0, min(top_k, 10))

        if not use_memory:
            return {"use_memory": False, "types": [], "top_k": 0}

        normalized = list(dict.fromkeys(normalized))
        if not normalized:
            return {"use_memory": False, "types": [], "top_k": 0}

        return {
            "use_memory": True,
            "types": normalized,
            "top_k": max(top_k, 1),
        }
