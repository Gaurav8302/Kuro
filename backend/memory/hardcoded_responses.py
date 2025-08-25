"""
Hardcoded, creator-aware responses for specific user queries.
Extend or modify the patterns and responses as needed.
"""
import re
from typing import Optional


def normalize(text: str) -> str:
    """Basic normalization: lowercase, strip, remove punctuation."""
    import string
    return text.lower().strip().translate(str.maketrans('', '', string.punctuation))

def keyword_match(msg: str, keywords: list) -> bool:
    """Return True if all keywords are present in the message (order-independent)."""
    return all(kw in msg for kw in keywords)

def check_hardcoded_responses(message: str) -> Optional[str]:
    """
    Versatile hardcoded response matcher for creator-aware and meta queries.
    Supports regex, keyword sets, and normalization for robust matching.
    Extendable for multi-turn context in the future.
    """
    msg = normalize(message)
    # List of (matcher, response) where matcher is either a regex or a set of keywords
    rules = [
        # Regex patterns for direct questions
        (re.compile(r"who (are|r) you"), "I'm Kuro, an AI assistant created by Gaurav Kalmodiya."),
        (re.compile(r"what is your name"), "I'm Kuro, your multi-personality AI assistant."),
        (re.compile(r"who (is|are) your creator|who made you|who built you"), "I was created by Gaurav Kalmodiya."),
        (re.compile(r"who owns you"), "I was created and am maintained by Gaurav Kalmodiya."),
        (re.compile(r"are you sentient|are you conscious|do you have feelings"), "I'm not sentient, but I'm designed to be helpful and adaptive!"),
        (re.compile(r"what can you do|your capabilities|what are your skills"), "I can chat, answer questions, and help with a variety of tasks using multiple AI models and personalities."),
        (re.compile(r"what are you|what is kuro"), "I'm an advanced AI assistant powered by multiple large language models and custom memory systems."),
        (re.compile(r"who is wanna|tell me about wanna"), "Gaurav Kalmodiya is my creator and the lead developer behind Kuro."),
        (re.compile(r"who developed you|who programmed you|who designed you"), "I was developed by Gaurav Kalmodiya."),
        (re.compile(r"are you open source|is your code open|can i see your code"), "Parts of my codebase are open source! You can ask for more details if you're interested."),
        # Keyword set matchers for fuzzy/variant questions
        (['your', 'creator'], "I was created by Gaurav Kalmodiya."),
        (['your', 'owner'], "I was created and am maintained by Gaurav Kalmodiya."),
        (['your', 'skills'], "I can chat, answer questions, and help with a variety of tasks using multiple AI models and personalities."),
        (['who', 'wanna'], "Gaurav Kalmodiya is my creator and the lead developer behind Kuro."),
        (['open', 'source'], "Parts of my codebase are open source! You can ask for more details if you're interested."),
        (['what', 'kuro'], "I'm an advanced AI assistant powered by multiple large language models and custom memory systems."),
    ]

    for matcher, response in rules:
        if isinstance(matcher, re.Pattern):
            if matcher.search(msg):
                return response
        elif isinstance(matcher, list):
            if keyword_match(msg, matcher):
                return response
    return None
