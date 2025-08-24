"""Summarization prompt templates for progressive conversation memory.

These templates are intentionally separate so they can be tuned without
touching logic code. Strategies:

aggressive  -> Lowest verbosity, strict compression of factual items
balanced    -> Middle ground (default)
verbose     -> Richer narrative; still structured

Output MUST be machine-friendly so the system can later parse / filter.
"""

STRATEGY_GUIDELINES = {
    "aggressive": {
        "target_chars": 400,
        "instructions": "Compress aggressively. Keep ONLY durable facts, preferences, goals, decisions, unresolved questions. Drop small talk."
    },
    "balanced": {
        "target_chars": 800,
        "instructions": "Summarize key events, reasoning steps, preferences, open tasks. Omit filler."
    },
    "verbose": {
        "target_chars": 1200,
        "instructions": "Include brief narrative flow plus all important facts, preferences, decisions, quotes (trim long quotes)."
    }
}

BASE_PROMPT = """
You are a conversation summarizer producing structured rolling memory chunks.

You will receive a contiguous block of chat exchanges (user + assistant turns).
Produce a concise knowledge-preserving summary following STRICT format rules.

REQUIREMENTS:
- Preserve IMPORTANT user facts: preferences (likes/dislikes), goals, plans, constraints, skills, name & profile attributes.
- Extract notable events, decisions, tasks, questions, emotional tone shifts.
- Keep short, verbatim key quotes (<12 words) only if they may be referenced later.
- Use deterministic, label-based sections EXACTLY as below (omit a section if empty):
  FACTS:
  PREFERENCES:
  GOALS:
  TASKS_OPEN:
  TASKS_COMPLETED:
  QUESTIONS_UNRESOLVED:
  EVENTS:
  QUOTES:
  OTHER_NOTES:
- Each section lists bullet items starting with '-'. No nested bullets.
- Avoid redundancy across sections. No commentary fluff.
- Never exceed ~{target_chars} characters total (hard cap ~{hard_cap}). If over, iteratively trim lowest value details from OTHER_NOTES then EVENTS then verbose phrasing.
- DO NOT invent information.

Return ONLY the sections (no intro/outro text). If everything is empty return FACTS: (blank line afterwards).

Block to summarize (chronological order):
"""

def build_summarization_prompt(block_text: str, strategy: str = "balanced") -> str:
    strat = STRATEGY_GUIDELINES.get(strategy, STRATEGY_GUIDELINES["balanced"])
    target = strat["target_chars"]
    hard_cap = int(target * 1.25)
    instructions = strat["instructions"]
    prompt = BASE_PROMPT.format(target_chars=target, hard_cap=hard_cap)
    prompt += f"\nSTRATEGY: {strategy.upper()} - {instructions}\n\n"
    prompt += block_text.strip() + "\n" \
              "\n---\nProduce summary now."
    return prompt
