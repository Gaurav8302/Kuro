"""Live Web & Browser Search Integration for Kuro AI.

Provides multi-tiered web search capabilities:
1. Tavily AI Search (TAVILY_API_KEY)
2. Serper Google Search (SERPER_API_KEY)
3. Brave Search (BRAVE_API_KEY)
4. Zero-Config Fallback (DuckDuckGo Instant Answer API + Wikipedia Search API)

Features:
- Fast asynchronous requests with configurable timeouts
- Automatic search intent detection for queries needing real-time info
- Markdown formatting with clickable source citations for prompt injection
- Graceful degradation if external services are unreachable
"""

from __future__ import annotations

import os
import re
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import httpx

logger = logging.getLogger(__name__)

# Search triggers for auto-detecting real-time information needs
SEARCH_INTENT_PATTERNS = [
    r"\b(search\s+(the\s+)?(web|internet|google)|look\s+up|google)\b",
    r"\b(latest|current|recent|today'?s?|breaking)\s+(news|price|updates?|release|score|weather|stock)\b",
    r"\b(what\s+is\s+the\s+current|what'?s\s+the\s+current|what\s+happened\s+today|today'?s\s+weather)\b",
    r"\b(who\s+won|score\s+of|stock\s+price\s+of|crypto\s+price|market\s+cap\s+of)\b",
    r"\b(when\s+was\s+.*released|release\s+date\s+of|latest\s+version\s+of)\b",
    r"https?://[^\s]+",  # Direct URLs
]

_COMPILED_SEARCH_PATTERNS = [re.compile(p, re.IGNORECASE) for p in SEARCH_INTENT_PATTERNS]


def detect_search_need(query: str) -> bool:
    """Detect whether a user query requires real-time live web search."""
    if not query or not query.strip():
        return False
    text = query.strip()
    for pattern in _COMPILED_SEARCH_PATTERNS:
        if pattern.search(text):
            return True
    return False


async def search_web(
    query: str,
    max_results: int = 5,
    timeout: float = 6.0,
) -> Dict[str, Any]:
    """Execute live web search using available provider cascade."""
    cleaned_query = query.strip()
    if not cleaned_query:
        return {
            "query": query,
            "provider": "none",
            "results": [],
            "searched_at": datetime.now(timezone.utc).isoformat(),
            "has_results": False,
        }

    # 1. Tavily AI Search (Preferred for LLM agent search)
    tavily_key = os.getenv("TAVILY_API_KEY", "").strip()
    if tavily_key:
        try:
            results = await _search_tavily(cleaned_query, tavily_key, max_results, timeout)
            if results:
                return {
                    "query": cleaned_query,
                    "provider": "tavily",
                    "results": results,
                    "searched_at": datetime.now(timezone.utc).isoformat(),
                    "has_results": True,
                }
        except Exception as e:
            logger.warning("Tavily search failed, falling back: %s", e)

    # 2. Serper Google Search
    serper_key = os.getenv("SERPER_API_KEY", "").strip()
    if serper_key:
        try:
            results = await _search_serper(cleaned_query, serper_key, max_results, timeout)
            if results:
                return {
                    "query": cleaned_query,
                    "provider": "serper",
                    "results": results,
                    "searched_at": datetime.now(timezone.utc).isoformat(),
                    "has_results": True,
                }
        except Exception as e:
            logger.warning("Serper search failed, falling back: %s", e)

    # 3. Brave Search
    brave_key = os.getenv("BRAVE_API_KEY", "").strip()
    if brave_key:
        try:
            results = await _search_brave(cleaned_query, brave_key, max_results, timeout)
            if results:
                return {
                    "query": cleaned_query,
                    "provider": "brave",
                    "results": results,
                    "searched_at": datetime.now(timezone.utc).isoformat(),
                    "has_results": True,
                }
        except Exception as e:
            logger.warning("Brave search failed, falling back: %s", e)

    # 4. Zero-Config Fallback: DuckDuckGo Instant Answer + Wikipedia Open Search
    try:
        results = await _search_duckduckgo_wikipedia(cleaned_query, max_results, timeout)
        return {
            "query": cleaned_query,
            "provider": "duckduckgo_wikipedia",
            "results": results,
            "searched_at": datetime.now(timezone.utc).isoformat(),
            "has_results": len(results) > 0,
        }
    except Exception as e:
        logger.warning("Zero-config search fallback failed: %s", e)
        return {
            "query": cleaned_query,
            "provider": "fallback_empty",
            "results": [],
            "searched_at": datetime.now(timezone.utc).isoformat(),
            "has_results": False,
        }


async def _search_tavily(
    query: str,
    api_key: str,
    max_results: int,
    timeout: float,
) -> List[Dict[str, str]]:
    url = "https://api.tavily.com/search"
    payload = {
        "api_key": api_key,
        "query": query,
        "max_results": max_results,
        "search_depth": "basic",
        "include_answer": False,
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("results", [])[:max_results]:
            results.append({
                "title": item.get("title", "Search Result"),
                "url": item.get("url", ""),
                "snippet": item.get("content", "")[:300],
                "source": "tavily",
            })
        return results


async def _search_serper(
    query: str,
    api_key: str,
    max_results: int,
    timeout: float,
) -> List[Dict[str, str]]:
    url = "https://google.serper.dev/search"
    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json={"q": query, "num": max_results}, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("organic", [])[:max_results]:
            results.append({
                "title": item.get("title", "Search Result"),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", "")[:300],
                "source": "google_serper",
            })
        return results


async def _search_brave(
    query: str,
    api_key: str,
    max_results: int,
    timeout: float,
) -> List[Dict[str, str]]:
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": api_key,
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get(url, params={"q": query, "count": max_results}, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("web", {}).get("results", [])[:max_results]:
            results.append({
                "title": item.get("title", "Search Result"),
                "url": item.get("url", ""),
                "snippet": item.get("description", "")[:300],
                "source": "brave",
            })
        return results


async def _search_duckduckgo_wikipedia(
    query: str,
    max_results: int,
    timeout: float,
) -> List[Dict[str, str]]:
    """Zero-config provider combining DuckDuckGo Instant Answer and Wikipedia."""
    results: List[Dict[str, str]] = []
    headers = {"User-Agent": "KuroAI-WebSearch/1.0 (https://kuro.ai; assistant@kuro.ai)"}

    async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
        # 1. DuckDuckGo Instant Answer
        try:
            ddg_resp = await client.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": "1", "skip_disambig": "0"},
            )
            if ddg_resp.status_code == 200:
                ddg_data = ddg_resp.json()
                abstract = (ddg_data.get("AbstractText") or "").strip()
                abstract_url = ddg_data.get("AbstractURL")
                heading = ddg_data.get("Heading") or query
                if abstract and abstract_url:
                    results.append({
                        "title": heading,
                        "url": abstract_url,
                        "snippet": abstract[:350],
                        "source": "duckduckgo",
                    })

                # Related topics
                for topic in ddg_data.get("RelatedTopics", []):
                    if len(results) >= max_results:
                        break
                    if isinstance(topic, dict) and "Text" in topic and "FirstURL" in topic:
                        results.append({
                            "title": topic["Text"].split(" - ")[0] if " - " in topic["Text"] else heading,
                            "url": topic["FirstURL"],
                            "snippet": topic["Text"][:300],
                            "source": "duckduckgo",
                        })
        except Exception as e:
            logger.debug("DuckDuckGo instant answer lookup failed: %s", e)

        # 2. Wikipedia Search API (clean, structured, encyclopedic factual knowledge)
        if len(results) < max_results:
            try:
                wiki_resp = await client.get(
                    "https://en.wikipedia.org/w/api.php",
                    params={
                        "action": "query",
                        "list": "search",
                        "srsearch": query,
                        "format": "json",
                        "utf8": 1,
                        "srlimit": max_results - len(results),
                    },
                )
                if wiki_resp.status_code == 200:
                    wiki_data = wiki_resp.json()
                    search_items = wiki_data.get("query", {}).get("search", [])
                    for item in search_items:
                        title = item.get("title", "")
                        raw_snippet = item.get("snippet", "")
                        clean_snippet = re.sub(r"<[^>]+>", "", raw_snippet).strip()
                        wiki_url = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
                        results.append({
                            "title": title,
                            "url": wiki_url,
                            "snippet": clean_snippet[:300],
                            "source": "wikipedia",
                        })
            except Exception as e:
                logger.debug("Wikipedia search lookup failed: %s", e)

    return results[:max_results]


def format_search_results_for_prompt(search_data: Optional[Dict[str, Any]]) -> str:
    """Format search results into structured markdown context for the LLM prompt."""
    if not search_data or not search_data.get("has_results"):
        return ""

    results = search_data.get("results", [])
    if not results:
        return ""

    query = search_data.get("query", "")
    provider = search_data.get("provider", "live_web")

    lines = [
        f"Live Web Search Results (Query: \"{query}\", Provider: {provider}):",
    ]
    for idx, item in enumerate(results, 1):
        title = item.get("title", f"Result {idx}")
        url = item.get("url", "")
        snippet = item.get("snippet", "").strip()
        lines.append(f"[{idx}] {title}")
        if snippet:
            lines.append(f"    Summary: {snippet}")
        if url:
            lines.append(f"    Source URL: {url}")

    lines.append(
        "\nInstructions for Web Results: Synthesize information from these search results accurately. "
        "Cite sources inline using Markdown links: [Source Title](URL)."
    )
    return "\n".join(lines)
