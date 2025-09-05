"""
Orchestrator Filter Layer for Kuro Chatbot

This module implements a pre-processing layer that sits between user queries 
and the main Kuro LLM. It uses OpenRouter models to analyze, classify, and 
expand user queries into optimized prompts for the downstream executor.

Features:
- Task classification (math, code, RAG, chat, other)
- Query expansion and prompt optimization
- JSON-based structured output
- Round-robin model selection from OpenRouter
- Safe JSON parsing with fallbacks
"""

import os
import json
import random
import logging
import asyncio
from typing import Dict, Any, Optional, List
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# OpenRouter models for orchestration (round-robin selection)
ORCHESTRATOR_MODELS = [
    "deepseek/deepseek-v3.1",
    "openai/gpt-oss-120b",
    "z-ai/glm-4.5-air",
    "moonshotai/kimi-k2"
]

# System prompt for the orchestrator
ORCHESTRATOR_SYSTEM_PROMPT = """You are an Orchestrator filter. Take raw user input and produce a single, high-quality instruction prompt for the downstream executor (Kuro). Output ONLY valid JSON. Do NOT solve the task. Do not include any explanation or extra text.

JSON schema:
{
"task": "<math|code|rag|chat|other>",
"input": "<cleaned user query or expression>",
"expanded_prompt": "<complete instruction prompt for the executor. include persona, constraints, tools, example IO if helpful>",
"instructions": ["<short step-by-step plan the executor should follow>"],
"tools": ["<suggested tools or solvers: sympy, pinecone, run_code, etc.>"],
"expected_response_format": "<e.g. JSON with fields, plain text, code block, markdown>",
"confidence": <0.0-1.0>
}

Rules:

1. Classify task precisely. If ambiguous, add clarifying step in "instructions".
2. Keep code blocks intact inside "input".
3. For math: put exact expression in "input", add step plan in "instructions". Do not compute.
4. For code: include language, expected function signature, minimal example I/O in "expanded_prompt".
5. For RAG: produce short search query + retrieval hints in "expanded_prompt".
6. For chat: add persona context if user hints at one, suggest tone and length.
7. Suggest tools in "tools".
8. Set "expected_response_format" to the most precise format.
9. Use "confidence" to indicate classification certainty.
10. If strict JSON fails, return fallback:
    {
    "task":"other",
    "input":"<original user text>",
    "expanded_prompt":"<keep original text>",
    "instructions":["forward to executor"],
    "tools":[],
    "expected_response_format":"text",
    "confidence":0.0
    }"""

class OrchestratorClient:
    """Client for making requests to OpenRouter API"""
    
    def __init__(self):
        self.api_key = os.environ.get("OPENROUTER_API_KEY")
        if not self.api_key:
            logger.error("OPENROUTER_API_KEY not found in environment variables")
            raise ValueError("OPENROUTER_API_KEY is required")
        
        self.base_url = "https://openrouter.ai/api/v1"
        self.current_model_index = 0
        
    def get_next_model(self) -> str:
        """Get the next model in round-robin fashion"""
        model = ORCHESTRATOR_MODELS[self.current_model_index]
        self.current_model_index = (self.current_model_index + 1) % len(ORCHESTRATOR_MODELS)
        return model
    
    async def _call_openrouter(self, model: str, user_text: str) -> str:
        """
        Make an async request to OpenRouter API
        
        Args:
            model (str): Model identifier for OpenRouter
            user_text (str): User's input text
            
        Returns:
            str: Raw response from the model
            
        Raises:
            Exception: If API request fails
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/Gaurav8302/Kuro",  # Optional
            "X-Title": "Kuro Chatbot"  # Optional
        }
        
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": ORCHESTRATOR_SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": user_text
                }
            ],
            "temperature": 0.3,  # Lower temperature for more consistent JSON output
            "max_tokens": 1000,   # Sufficient for orchestration JSON
            "top_p": 0.9
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                if not content:
                    raise Exception("Empty response from OpenRouter")
                
                logger.info(f"✅ OpenRouter orchestration successful with {model}")
                return content
                
            except httpx.TimeoutException:
                logger.error(f"❌ OpenRouter request timeout for {model}")
                raise Exception(f"Request timeout for model {model}")
            except httpx.HTTPStatusError as e:
                logger.error(f"❌ OpenRouter HTTP error {e.response.status_code} for {model}")
                raise Exception(f"HTTP {e.response.status_code}: {e.response.text}")
            except Exception as e:
                logger.error(f"❌ OpenRouter request failed for {model}: {str(e)}")
                raise

def _parse_json_safe(text: str) -> Dict[str, Any]:
    """
    Safely parse JSON from model output with fallback
    
    Args:
        text (str): Raw text that should contain JSON
        
    Returns:
        Dict[str, Any]: Parsed JSON or fallback structure
    """
    try:
        # Try to find JSON in the response (might have extra text)
        text = text.strip()
        
        # Look for JSON object boundaries
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_text = text[start_idx:end_idx + 1]
            parsed = json.loads(json_text)
            
            # Validate required fields
            required_fields = ["task", "input", "expanded_prompt", "instructions", "tools", "expected_response_format", "confidence"]
            if all(field in parsed for field in required_fields):
                logger.info("✅ Successfully parsed orchestrator JSON")
                return parsed
            else:
                logger.warning("⚠️ JSON missing required fields, using fallback")
        
    except json.JSONDecodeError as e:
        logger.warning(f"⚠️ JSON parsing failed: {str(e)}")
    except Exception as e:
        logger.warning(f"⚠️ Unexpected error in JSON parsing: {str(e)}")
    
    # Fallback structure
    fallback = {
        "task": "other",
        "input": text[:500] if text else "empty query",  # Limit fallback input length
        "expanded_prompt": text[:500] if text else "Please provide a response to the user's query.",
        "instructions": ["forward to executor"],
        "tools": [],
        "expected_response_format": "text",
        "confidence": 0.0
    }
    
    logger.info("🔄 Using fallback JSON structure")
    return fallback

# Global orchestrator client instance
_orchestrator_client = None

def get_orchestrator_client() -> OrchestratorClient:
    """Get or create the global orchestrator client instance"""
    global _orchestrator_client
    if _orchestrator_client is None:
        try:
            _orchestrator_client = OrchestratorClient()
            logger.info("✅ Orchestrator client initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize orchestrator client: {str(e)}")
            raise
    return _orchestrator_client

async def orchestrate(user_query: str, session_meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Main orchestration function - analyzes user query and produces structured output
    
    Args:
        user_query (str): Raw user input
        session_meta (Optional[Dict[str, Any]]): Session metadata (user_id, session_id, etc.)
        
    Returns:
        Dict[str, Any]: Structured orchestration result with expanded prompt and task info
        
    Example return:
        {
            "task": "math",
            "input": "solve x^2 + 5x + 6 = 0",
            "expanded_prompt": "You are a math tutor. Solve the quadratic equation step by step...",
            "instructions": ["identify equation type", "apply quadratic formula", "show work"],
            "tools": ["sympy"],
            "expected_response_format": "step-by-step solution with final answer",
            "confidence": 0.95
        }
    """
    if not user_query or not user_query.strip():
        logger.warning("⚠️ Empty user query provided to orchestrator")
        return {
            "task": "other",
            "input": "",
            "expanded_prompt": "Please provide a question or message for me to help with.",
            "instructions": ["request user input"],
            "tools": [],
            "expected_response_format": "text",
            "confidence": 0.0
        }
    
    try:
        # Get orchestrator client
        client = get_orchestrator_client()
        
        # Select model using round-robin
        selected_model = client.get_next_model()
        logger.info(f"🎯 Using orchestrator model: {selected_model}")
        
        # Add session context to query if available
        enhanced_query = user_query
        if session_meta:
            user_id = session_meta.get("user_id", "unknown")
            session_id = session_meta.get("session_id")
            context_note = f"\n[Context: user_id={user_id}"
            if session_id:
                context_note += f", session_id={session_id}"
            context_note += "]"
            enhanced_query = user_query + context_note
        
        # Call OpenRouter model with timeout
        try:
            raw_response = await asyncio.wait_for(
                client._call_openrouter(selected_model, enhanced_query),
                timeout=25.0  # Slightly less than the httpx timeout to allow proper error handling
            )
            logger.debug(f"🔄 Raw orchestration response length: {len(raw_response)} chars")
        except asyncio.TimeoutError:
            logger.error(f"❌ Orchestration timeout after 25s with model {selected_model}")
            raise Exception("Orchestration request timed out")
        
        # Parse JSON safely
        orchestration_result = _parse_json_safe(raw_response)
        
        # Validate confidence range
        confidence = orchestration_result.get("confidence", 0.0)
        if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
            logger.warning(f"⚠️ Invalid confidence value {confidence}, clamping to [0,1]")
            orchestration_result["confidence"] = max(0.0, min(1.0, float(confidence) if confidence else 0.0))
        
        # Log successful orchestration
        logger.info(f"✅ Orchestration completed: task={orchestration_result['task']}, confidence={orchestration_result['confidence']:.2f}")
        
        return orchestration_result
        
    except Exception as e:
        logger.error(f"❌ Orchestration failed: {str(e)}")
        
        # Return safe fallback
        return {
            "task": "other",
            "input": user_query,
            "expanded_prompt": user_query,
            "instructions": ["process user query directly"],
            "tools": [],
            "expected_response_format": "text",
            "confidence": 0.0,
            "error": str(e)
        }

# Backward compatibility functions (sync versions)
def orchestrate_sync(user_query: str, session_meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Synchronous wrapper for orchestrate function
    
    Args:
        user_query (str): Raw user input
        session_meta (Optional[Dict[str, Any]]): Session metadata
        
    Returns:
        Dict[str, Any]: Orchestration result
    """
    try:
        # Check if we're already in an async context
        try:
            asyncio.get_running_loop()
            logger.warning("⚠️ orchestrate_sync called from async context - this may cause deadlocks")
            # Return low-confidence fallback to avoid deadlock
            return {
                "task": "other",
                "input": user_query,
                "expanded_prompt": user_query,
                "instructions": ["process user query directly"],
                "tools": [],
                "expected_response_format": "text",
                "confidence": 0.0,
                "error": "sync_in_async_context"
            }
        except RuntimeError:
            # Not in an async context, safe to use run_until_complete
            logger.debug("🔄 Running orchestration in new event loop")
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                return loop.run_until_complete(orchestrate(user_query, session_meta))
            finally:
                loop.close()
                asyncio.set_event_loop(None)
    except Exception as e:
        logger.error(f"❌ Sync orchestration failed: {str(e)}")
        return {
            "task": "other",
            "input": user_query,
            "expanded_prompt": user_query,
            "instructions": ["process user query directly"],
            "tools": [],
            "expected_response_format": "text",
            "confidence": 0.0,
            "error": str(e)
        }

if __name__ == "__main__":
    # Simple test
    import asyncio
    
    async def test_orchestrator():
        """Test the orchestrator with sample queries"""
        test_queries = [
            "solve x^2 + 5x + 6 = 0",
            "write a Python function to reverse a string",
            "what do you remember about our last conversation?",
            "hello, how are you?",
            "calculate the derivative of sin(x^2)"
        ]
        
        for query in test_queries:
            print(f"\n🔍 Testing: {query}")
            try:
                result = await orchestrate(query)
                print(f"✅ Task: {result['task']}")
                print(f"🎯 Confidence: {result['confidence']}")
                print(f"📝 Instructions: {result['instructions']}")
                print(f"🛠️ Tools: {result['tools']}")
            except Exception as e:
                print(f"❌ Error: {str(e)}")
    
    # Run the test if file is executed directly
    if os.environ.get("OPENROUTER_API_KEY"):
        asyncio.run(test_orchestrator())
    else:
        print("❌ OPENROUTER_API_KEY not set. Cannot run test.")
