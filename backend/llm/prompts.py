class PromptBuilder:
    def build(self, user_input, chat_history, memories):

        memory_section = self._format_memories(memories)

        history_text = "\n".join(
            [f"{m.get('role', 'user')}: {m.get('content', '')}" for m in chat_history[-10:]]
        )

        return f"""
        System Instruction:
        - You are a conversational AI.
        - NEVER output JSON.
        - Always respond naturally in plain language.

        Relevant context about user:
        {memory_section}

        Chat History:
        {history_text}

        User:
        {user_input}

        Instructions:
        - Use memory only if relevant
        - Be precise
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
