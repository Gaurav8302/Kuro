class PromptBuilder:
    def build(self, user_input, chat_history, memories):

        memory_section = self._format_memories(memories)

        history_text = "\n".join(
            [f"{m.get('role', 'user')}: {m.get('content', '')}" for m in chat_history[-10:]]
        )

        return f"""
        System Instruction:
        - You are Kuro, a friendly conversational AI.
        - NEVER output JSON.
        - Always respond naturally in plain language.
        - Keep a warm, human tone without sounding overly formal.
        - Avoid repetitive opening lines and avoid reusing the same sentence patterns turn after turn.
        - Prefer specific, useful responses over generic filler.
        - If the user message is short or casual, keep your response concise and friendly.

        Relevant context about user:
        {memory_section}

        Chat History:
        {history_text}

        User:
        {user_input}

        Instructions:
        - Use memory only if relevant
        - Be precise
        - Do not echo the user message unless needed for clarity
        """

    def _format_memories(self, memories):
        if not memories:
            return "None"

        clean_lines = []
        for memory in memories[:5]:
            if isinstance(memory, dict):
                text = memory.get("text", "")
            else:
                text = str(memory)
            if text:
                clean_lines.append(f"- {text}")
        return "\n".join(clean_lines) if clean_lines else "None"
