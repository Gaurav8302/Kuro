class PromptBuilder:
    def build(self, user_input, chat_history, memories):

        memory_section = self._format_memories(memories)

        history_text = "\n".join(
            [f"{m.get('role', 'user')}: {m.get('content', '')}" for m in chat_history[-10:]]
        )

        return f"""
        Relevant Memory:
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

        return "\n".join([f"- {m}" for m in memories])
