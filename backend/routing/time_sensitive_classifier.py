"""Time-Sensitive Query Classifier.

Detects queries that require real-time information BEFORE the LLM answers.
Returns a classification with three tiers:

  HIGH_RISK  (confidence >= 0.85) — Skip LLM entirely, return safe response.
  BORDERLINE (confidence 0.40–0.84) — Generate LLM draft, then verify it.
  SAFE       (confidence < 0.40) — Normal LLM generation, no verification.

Uses keyword + semantic cross-matching (no LLM call needed):
  - Leader terms × context  → HIGH_RISK
  - Temporal terms alone    → varies by overlap
  - Domain terms            → HIGH_RISK or BORDERLINE depending on specificity
"""
from __future__ import annotations

import re
import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Term lists for cross-matching (lowercased, no regex)
# ---------------------------------------------------------------------------

# Leadership titles — presence alone is moderate risk; with context → high
LEADER_TERMS: List[str] = [
    "president",
    "prime minister",
    "pm",
    "chief minister",
    "cm",
    "governor",
    "chancellor",
    "mayor",
    "king",
    "queen",
    "ruler",
    "head of state",
    "minister",
    "secretary of state",
    "chief justice",
    "speaker of the house",
    "vice president",
    "vp",
    "deputy pm",
    "defence minister",
    "defense minister",
    "finance minister",
    "home minister",
    "foreign minister",
    "mla",
    "mp",  # member of parliament context
    "senator",
    "congressman",
    "congresswoman",
]

# Context that amplifies leader terms to HIGH_RISK
LEADER_CONTEXT: List[str] = [
    # Countries
    "india", "usa", "us", "uk", "nepal", "china", "russia", "japan", "pakistan",
    "germany", "france", "canada", "australia", "brazil", "mexico", "italy",
    "spain", "south korea", "north korea", "iran", "iraq", "israel", "ukraine",
    "sri lanka", "bangladesh", "afghanistan", "egypt", "nigeria", "south africa",
    "indonesia", "thailand", "turkey", "saudi arabia", "argentina", "america",
    "britain", "england",
    # Indian states
    "madhya pradesh", "mp", "uttar pradesh", "up", "maharashtra", "bihar",
    "rajasthan", "tamil nadu", "karnataka", "kerala", "punjab", "haryana",
    "gujarat", "west bengal", "odisha", "telangana", "andhra pradesh",
    "jharkhand", "chhattisgarh", "uttarakhand", "goa", "assam", "himachal",
    "tripura", "meghalaya", "manipur", "nagaland", "mizoram", "sikkim",
    "arunachal", "delhi", "jammu", "kashmir",
]

# Temporal indicators — user asking about "now"
TEMPORAL_TERMS: List[str] = [
    "current", "currently",
    "latest", "newest",
    "today", "tonight", "this morning",
    "right now", "as of now",
    "this week", "this month", "this year",
    "yesterday", "last night",
    "just announced", "just happened", "just released", "just launched",
    "recent", "recently",
    "now",
    "as of",
    "up to date",
    "breaking",
    "trending",
    "live",
    "ongoing",
    "last",  # "last world cup", "last election"
]

# Inherently time-sensitive domains
DOMAIN_TERMS: List[str] = [
    "news",
    "election", "election result", "election winner",
    "vote", "voting", "voted",
    "stock price", "stock market", "share price", "nifty", "sensex",
    "crypto price", "bitcoin price", "ethereum price",
    "cryptocurrency",
    "weather", "forecast",
    "score", "scorecard",
    "match result", "match winner",
    "who won", "who is winning", "who lost",
    "price of", "how much is", "how much does",
    "what happened",
    "update on",
    "new release", "release date",
    "when does", "when will", "when did",
    "came out", "launched today",
    "ipo",
    "budget 2024", "budget 2025", "budget 2026",
    "box office", "boxoffice",
    "world cup",
    "olympics",
    "gdp", "inflation rate",
    "interest rate",
    "exchange rate",
    "population",
    "ranking",  # "world ranking", "icc ranking"
    "pandemic", "outbreak",
    "war", "conflict",
]

# ---------------------------------------------------------------------------
# Compiled regex patterns for precise matching
# ---------------------------------------------------------------------------
# Political patterns (regex for word-boundary matching)
_POLITICAL_PATTERNS: List[str] = [
    r"\bpresident\b",
    r"\bprime\s*minister\b",
    r"\bchief\s*minister\b",
    r"\bgovernor\b",
    r"\bchancellor\b",
    r"\bmayor\b",
    r"\bhead of state\b",
    r"\bminister of\b",
    r"\bsecretary of state\b",
    r"\bsupreme court\s+(chief\s+)?justice\b",
    r"\b(who|what) (is|was|are) (the )?(current )?(leader|head|pm|cm|president|prime\s*minister|chief\s*minister)\b",
    # Abbreviation patterns with context
    r"\bcm\s+(of|in)\s+\w+",          # "cm of mp", "cm of maharashtra"
    r"\bpm\s+(of|in)\s+\w+",          # "pm of india", "pm of nepal"
    r"\bvp\s+(of|in)\s+\w+",          # "vp of india"
]

# Temporal patterns (regex)
_TEMPORAL_PATTERNS: List[str] = [
    r"\bcurrent(ly)?\b",
    r"\blatest\b",
    r"\btoday\b",
    r"\bright now\b",
    r"\bthis (week|month|year)\b",
    r"\byesterday\b",
    r"\blast night\b",
    r"\bjust (announced|happened|released|launched)\b",
    r"\brecent(ly)?\b",
    r"\bas of\b",
    r"\bup to date\b",
    r"\bbreaking\b",
    r"\btrending\b",
    r"\blive\b",
    r"\bongoing\b",
]

# Domain patterns (regex)
_DOMAIN_PATTERNS: List[str] = [
    r"\bnews\b",
    r"\belection\b",
    r"\bvot(e|ing|ed)\b",
    r"\bstock (price|market)\b",
    r"\bshare price\b",
    r"\bnifty\b",
    r"\bsensex\b",
    r"\bcrypto(currency)?\s*(price|market|value)\b",
    r"\bbitcoin\s*price\b",
    r"\bweather\b",
    r"\bscore(card)?\b",
    r"\bmatch (result|winner)\b",
    r"\bwho won\b",
    r"\bwho is winning\b",
    r"\bwho lost\b",
    r"\bprice of\b",
    r"\bhow much (is|does|are)\b",
    r"\bwhat happened\b",
    r"\bupdate on\b",
    r"\bnew release\b",
    r"\brelease date\b",
    r"\bwhen (does|will|did)\b",
    r"\bcame out\b",
    r"\blaunched today\b",
    r"\bipo\b",
    r"\bbudget\s+\d{4}\b",
    r"\bbox\s*office\b",
    r"\bworld cup\b",
    r"\bolympics\b",
    r"\bgdp\b",
    r"\binflation\s*rate\b",
    r"\binterest\s*rate\b",
    r"\bexchange\s*rate\b",
    r"\bwar\b",
]

# Ambiguous "who is" patterns that need clarification (exact-ish match)
_AMBIGUOUS_PATTERNS: List[str] = [
    r"^who\s+is\s+the\s+president\s*\??$",
    r"^who\s+is\s+the\s+pm\s*\??$",
    r"^who\s+is\s+the\s+prime\s*minister\s*\??$",
    r"^who\s+is\s+the\s+chief\s*minister\s*\??$",
    r"^who\s+is\s+the\s+cm\s*\??$",
    r"^who\s+is\s+the\s+leader\s*\??$",
    r"^who\s+is\s+the\s+governor\s*\??$",
    r"^who\s+is\s+the\s+mayor\s*\??$",
]

# Compile everything once
_compiled_political = [re.compile(p, re.IGNORECASE) for p in _POLITICAL_PATTERNS]
_compiled_temporal = [re.compile(p, re.IGNORECASE) for p in _TEMPORAL_PATTERNS]
_compiled_domain = [re.compile(p, re.IGNORECASE) for p in _DOMAIN_PATTERNS]
_compiled_ambiguous = [re.compile(p, re.IGNORECASE) for p in _AMBIGUOUS_PATTERNS]


# ---------------------------------------------------------------------------
# Term-presence helpers (fast substring check on lowercased query)
# ---------------------------------------------------------------------------

def _has_any_term(text: str, terms: List[str]) -> Tuple[bool, str]:
    """Check if any term appears with token boundaries. Returns (found, matched_term)."""
    for term in terms:
        # Prevent substring false positives like "improve" matching "mp".
        escaped = re.escape(term).replace(r"\ ", r"\s+")
        pattern = rf"(?<!\w){escaped}(?!\w)"
        if re.search(pattern, text, re.IGNORECASE):
            return True, term
    return False, ""


def _count_signal_hits(q_lower: str) -> Dict[str, Any]:
    """Count how many signal categories fire for a query.

    Returns dict with:
      leader_hit (bool), leader_term (str),
      context_hit (bool), context_term (str),
      temporal_hit (bool), temporal_term (str),
      domain_hit (bool), domain_term (str),
      regex_political (bool), regex_temporal (bool), regex_domain (bool)
    """
    leader_hit, leader_term = _has_any_term(q_lower, LEADER_TERMS)
    context_hit, context_term = _has_any_term(q_lower, LEADER_CONTEXT)
    temporal_hit, temporal_term = _has_any_term(q_lower, TEMPORAL_TERMS)
    domain_hit, domain_term = _has_any_term(q_lower, DOMAIN_TERMS)

    regex_political = any(p.search(q_lower) for p in _compiled_political)
    regex_temporal = any(p.search(q_lower) for p in _compiled_temporal)
    regex_domain = any(p.search(q_lower) for p in _compiled_domain)

    return {
        "leader_hit": leader_hit, "leader_term": leader_term,
        "context_hit": context_hit, "context_term": context_term,
        "temporal_hit": temporal_hit, "temporal_term": temporal_term,
        "domain_hit": domain_hit, "domain_term": domain_term,
        "regex_political": regex_political,
        "regex_temporal": regex_temporal,
        "regex_domain": regex_domain,
    }


# ---------------------------------------------------------------------------
# Main classifier
# ---------------------------------------------------------------------------

def classify_time_sensitivity(query: str) -> Dict[str, Any]:
    """Classify whether a query requires real-time information.

    Three-tier output:
      HIGH_RISK  (confidence >= 0.85): Skip LLM, return safe response.
      BORDERLINE (confidence 0.40–0.84): LLM draft + verifier.
      SAFE       (confidence < 0.40): Normal generation.

    Returns:
        Dict with keys:
          - is_time_sensitive (bool)
          - needs_clarification (bool)
          - category (str): "political", "temporal", "domain", "ambiguous", "safe"
          - reason (str): Human-readable explanation for UI display
          - confidence (float): 0.0 to 1.0
    """
    q = query.strip()
    q_lower = q.lower()

    # Skip very short queries or greetings
    if len(q_lower) < 4 or q_lower in ("hi", "hello", "hey", "thanks", "ok", "bye", "yo", "sup"):
        return _safe_result("short_greeting", 0.05)

    # --- Ambiguous patterns (exact match, highest priority) ---
    for pat in _compiled_ambiguous:
        if pat.search(q_lower):
            logger.info("Ambiguous query detected: %.80s", q)
            return {
                "is_time_sensitive": True,
                "needs_clarification": True,
                "category": "ambiguous",
                "reason": "This question may refer to different countries or regions. A bit more context would help me give you the right answer.",
                "confidence": 0.95,
            }

    # --- Gather all signal hits ---
    hits = _count_signal_hits(q_lower)

    # --- Scoring logic ---

    # TIER 1: Leader term + context (country/state) → HIGH_RISK
    # e.g. "pm of nepal", "cm of mp", "president of usa"
    if hits["leader_hit"] and hits["context_hit"]:
        reason = (
            f"This question is about political leadership ({hits['leader_term']}) "
            f"in {hits['context_term']}, which may have changed since my training data."
        )
        logger.info("HIGH_RISK: leader+context for: %.80s", q)
        return _sensitive_result("political", reason, 0.95)

    # Leader term + regex political pattern → HIGH_RISK
    if hits["leader_hit"] and hits["regex_political"]:
        reason = (
            f"This question involves political leadership ({hits['leader_term']}). "
            "Political roles change over time, so my information may be outdated."
        )
        logger.info("HIGH_RISK: leader+regex_political for: %.80s", q)
        return _sensitive_result("political", reason, 0.92)

    # Domain term with high specificity → HIGH_RISK
    # e.g. "bitcoin price", "stock market", "election result", "who won the world cup"
    if hits["domain_hit"] and (hits["temporal_hit"] or hits["regex_temporal"]):
        reason = (
            f"This question involves time-sensitive information ({hits['domain_term']}) "
            "that I may not have the latest data on."
        )
        logger.info("HIGH_RISK: domain+temporal for: %.80s", q)
        return _sensitive_result("domain", reason, 0.90)

    # Strong domain terms alone (news, election, score, who won, price) → HIGH_RISK
    high_risk_domains = [
        "news", "election", "who won", "who lost", "score",
        "stock price", "share price", "bitcoin price", "weather",
        "match result", "match winner", "world cup", "box office",
        "nifty", "sensex", "ipo", "what happened",
    ]
    if any(d in q_lower for d in high_risk_domains):
        matched = next(d for d in high_risk_domains if d in q_lower)
        reason = (
            f"This question is about {matched}, which changes frequently. "
            "My data may not reflect the latest situation."
        )
        logger.info("HIGH_RISK: strong domain '%s' for: %.80s", matched, q)
        return _sensitive_result("domain", reason, 0.88)

    # Leader term alone (no context/country) → BORDERLINE
    # e.g. "who is the president of..." or just "president"
    if hits["leader_hit"]:
        reason = (
            f"This question mentions a leadership role ({hits['leader_term']}). "
            "I'll answer, but leadership positions change, so let me verify."
        )
        logger.info("BORDERLINE: leader_term alone for: %.80s", q)
        return _sensitive_result("political", reason, 0.65)

    # Regex political match alone → BORDERLINE
    if hits["regex_political"]:
        reason = "This appears to involve political leadership, which changes over time."
        logger.info("BORDERLINE: regex_political for: %.80s", q)
        return _sensitive_result("political", reason, 0.60)

    # Domain term alone → BORDERLINE
    if hits["domain_hit"]:
        reason = (
            f"This question involves a topic ({hits['domain_term']}) "
            "that may require up-to-date information."
        )
        logger.info("BORDERLINE: domain_term alone for: %.80s", q)
        return _sensitive_result("domain", reason, 0.55)

    # Regex domain match alone → BORDERLINE
    if hits["regex_domain"]:
        reason = "This topic may involve information that changes over time."
        logger.info("BORDERLINE: regex_domain for: %.80s", q)
        return _sensitive_result("domain", reason, 0.50)

    # Temporal term alone → LOW BORDERLINE
    # "latest" or "current" could be about anything — moderate risk
    if hits["temporal_hit"] or hits["regex_temporal"]:
        reason = "This question uses time-related language, suggesting it may need recent information."
        logger.info("BORDERLINE: temporal for: %.80s", q)
        return _sensitive_result("temporal", reason, 0.45)

    # No signals detected → SAFE
    return _safe_result("no_time_sensitive_signals", 0.1)


# ---------------------------------------------------------------------------
# Result builders
# ---------------------------------------------------------------------------

def _sensitive_result(category: str, reason: str, confidence: float) -> Dict[str, Any]:
    return {
        "is_time_sensitive": True,
        "needs_clarification": False,
        "category": category,
        "reason": reason,
        "confidence": confidence,
    }


def _safe_result(reason: str, confidence: float) -> Dict[str, Any]:
    return {
        "is_time_sensitive": False,
        "needs_clarification": False,
        "category": "safe",
        "reason": reason,
        "confidence": confidence,
    }


# ---------------------------------------------------------------------------
# Safe response templates (with reasons shown to user)
# ---------------------------------------------------------------------------

def get_safe_response(classification: Dict[str, Any], query: str = "") -> str:
    """Generate a safe response based on the classification result.

    Includes the reason so the user understands WHY Kuro suggests search
    instead of answering directly — this feels intentional, not like a failure.
    """
    category = classification.get("category", "safe")
    reason = classification.get("reason", "")

    if category == "ambiguous":
        q_lower = query.lower()
        clarification = "Could you provide more specific details?"
        for keyword, question in _CLARIFICATION_QUESTIONS.items():
            if keyword in q_lower:
                clarification = question
                break
        return (
            f"{clarification}\n\n"
            "Since this involves leadership information that changes over time, "
            "I'd also recommend enabling **browser search** (🌐) for the most current answer."
        )

    # Build response with reason
    response_parts = []
    if reason:
        response_parts.append(reason)
    else:
        response_parts.append(
            "My knowledge may not include the latest information for this topic."
        )
    response_parts.append(
        "\nYou can enable **browser search** (🌐) to get the most recent, verified information."
    )
    return "\n".join(response_parts)


# Clarification questions for ambiguous patterns
_CLARIFICATION_QUESTIONS: dict[str, str] = {
    "president": "Which country's president are you asking about?",
    "pm": "Which country's Prime Minister are you asking about?",
    "prime minister": "Which country's Prime Minister are you asking about?",
    "chief minister": "Which state's Chief Minister are you asking about?",
    "cm": "Which state's Chief Minister are you asking about?",
    "leader": "Which country or organization's leader are you asking about?",
    "governor": "Which state's Governor are you asking about?",
    "mayor": "Which city's Mayor are you asking about?",
}


__all__ = [
    "classify_time_sensitivity",
    "get_safe_response",
]
