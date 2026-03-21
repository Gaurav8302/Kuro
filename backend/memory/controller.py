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
                if "use_memory" in decision and "types" in decision:
                    return decision
            except Exception:
                pass # Fallback to rule-based

        # Fallback to rule logic, taking the previous logic and enhancing it
        if not intent_data.get("needs_memory"):
            return {"use_memory": False, "types": [], "top_k": 0}

        intent = intent_data.get("intent", "general")

        # dynamic rules
        if intent in ["personal", "project", "learning"]:
            return {"use_memory": True, "types": ["facts", "preferences", "events"], "top_k": 10}

        if intent == "casual":
            return {"use_memory": False, "types": [], "top_k": 0}

        types = intent_data.get("memory_types", [])
        return {
            "use_memory": bool(types), 
            "types": types, 
            "top_k": 5
        }
