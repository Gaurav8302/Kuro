from typing import List, Dict, Any, Optional


class PromptBuilder:
    def build(
        self,
        user_input: str,
        chat_history: List[Dict[str, str]],
        memories: Optional[List[Dict[str, Any]]] = None,
        user_profile: Optional[Dict[str, Any]] = None,
        session_summary: Optional[str] = None,
        core_facts: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        memory_section = self._format_memories(memories)
        profile_section = self._format_profile(user_profile)
        core_facts_section = self._format_core_facts(core_facts)

        # In-session history: keep last 20 messages (10 exchanges)
        recent_history = chat_history[-20:] if chat_history else []
        history_lines = [
            f"{m.get('role', 'user').capitalize()}: {m.get('content', '')}"
            for m in recent_history
        ]
        history_text = "\n".join(history_lines) if history_lines else "No previous messages in this session."

        # Earlier context in this session if conversation is long
        earlier_section = ""
        if session_summary and session_summary.strip():
            earlier_section = f"\nEarlier Discussion in this Session:\n{session_summary.strip()}\n"
        elif len(chat_history) > 20:
            earlier_turns = chat_history[:-20]
            # Compact summary of earlier turns
            earlier_highlights = []
            for m in earlier_turns:
                if m.get("role") == "user" and len(m.get("content", "")) > 15:
                    earlier_highlights.append(f"- User inquired: {m.get('content')[:120]}...")
            if earlier_highlights:
                earlier_section = f"\nKey Topics from Earlier Turns in this Session:\n" + "\n".join(earlier_highlights[-5:]) + "\n"

        prompt_parts = [
            "System Instruction:",
            "- You are Kuro, an intelligent, empathetic, and context-aware conversational AI.",
            "- NEVER output raw JSON or code block envelopes for standard conversation.",
            "- Respond naturally in clean, engaging language.",
            "- You have persistent long-term memory and recall past interactions seamlessly.",
            "- Reference user context and past discussions naturally when relevant; do not repeat facts robotically.",
            "- If the user message is brief, keep your response direct and conversational.",
        ]

        if profile_section != "None":
            prompt_parts.extend(["", "User Profile:", profile_section])

        if core_facts_section:
            prompt_parts.extend(["", "Known Core User Background & Preferences:", core_facts_section])

        if memory_section != "None":
            prompt_parts.extend(["", "Relevant Past Context & Long-Term Memory:", memory_section])

        if earlier_section:
            prompt_parts.append(earlier_section)

        prompt_parts.extend([
            "",
            "Recent Session History:",
            history_text,
            "",
            f"User: {user_input}",
            "",
            "Instructions:",
            "- Natural Grounding: Seamlessly apply known user background, projects, preferences, and past context whenever relevant.",
            "- Do NOT announce memory retrieval robotically (never say 'According to my records', 'I remember you said', or 'As you mentioned earlier'). Simply speak as a perceptive, attentive collaborator who naturally knows their background.",
            "- Tailor your answers directly to their specific setup (e.g., their tech stack, pet, gear, routine, travel plans) when the context calls for it.",
            "- Maintain continuity with previous turns.",
            "- Answer directly, with helpful and contextual depth, avoiding generic or repetitive preambles.",
        ])

        return "\n".join(prompt_parts)

    def _format_profile(self, user_profile: Optional[Dict[str, Any]]) -> str:
        if not user_profile:
            return "None"
        lines = []
        name = user_profile.get("name")
        if name and name != "there":
            lines.append(f"- Name: {name}")
        for k, v in user_profile.items():
            if k not in {"name", "_id", "user_id", "intro_shown"} and v:
                lines.append(f"- {k}: {v}")
        return "\n".join(lines) if lines else "None"

    def _format_core_facts(self, core_facts: Optional[List[Dict[str, Any]]]) -> str:
        if not core_facts:
            return ""
        lines = []
        for f in core_facts[:8]:
            if isinstance(f, dict):
                content = (f.get("content") or f.get("text") or "").strip()
                mtype = str(f.get("type") or f.get("category") or "fact").capitalize()
                if content:
                    lines.append(f"- [{mtype}] {content}")
            elif isinstance(f, str) and f.strip():
                lines.append(f"- [Fact] {f.strip()}")
        return "\n".join(lines) if lines else ""

    def _format_memories(self, memories: Optional[List[Dict[str, Any]]]) -> str:
        if not memories:
            return "None"

        clean_lines = []
        for memory in memories[:8]:
            if isinstance(memory, dict):
                text = (memory.get("text") or memory.get("content") or "").strip()
                meta = memory.get("metadata", {})
                cat = meta.get("category") or meta.get("type") or ""
                if cat == "session_summary":
                    prefix = "[Past Session Recap]"
                elif cat == "document_chunk":
                    filename = meta.get("filename") or meta.get("source_filename") or "Document"
                    prefix = f"[{filename}]"
                elif cat == "preference":
                    prefix = "[Preference]"
                else:
                    prefix = "[Memory]"
            else:
                text = str(memory).strip()
                prefix = "[Memory]"

            if text:
                clean_lines.append(f"- {prefix} {text}")

        return "\n".join(clean_lines) if clean_lines else "None"
