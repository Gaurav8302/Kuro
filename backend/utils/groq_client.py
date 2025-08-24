"""
Groq API Client for LLaMA 3 70B Model

This module provides a clean interface to interact with Groq's LLaMA 3 70B model
using OpenAI-compatible chat completions API.
"""

import os
import json
import logging
import requests
from typing import Optional, Dict, Any, List, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

from routing.model_router import route_model
from reliability.circuit_breaker import allow_request, record_failure, record_success
from reliability.fallback_router import choose_fallback
from utils.token_estimator import estimate_tokens, trim_messages
from config.config_loader import get_model

class GroqClient:
    """
    Groq API client for LLaMA 3 70B model
    
    Provides a simple interface to generate chat completions using
    Groq's fast inference API with LLaMA 3 70B model.
    """
    
    def __init__(self):
        """Initialize the Groq client"""
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable is required")
        
        self.base_url = "https://api.groq.com/openai/v1"
        self.model = "llama3-70b-8192"
        
        # Default parameters
        self.default_params = {
            "temperature": 0.7,
            "max_tokens": 1024,
            "top_p": 1,
            "stream": False
        }
        
        logger.info("✅ Groq client initialized successfully")
    
    def _prepare_messages(self, prompt: str, system_instruction: Optional[str]) -> List[Dict[str,str]]:
        messages: List[Dict[str,str]] = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})
        return messages

    def _select_model(self, messages: List[Dict[str,str]], intent: Optional[str]) -> Tuple[str,str]:
        est_tokens = estimate_tokens(" ".join(m["content"] for m in messages))
        routing = route_model(messages[-1]["content"], est_tokens, intent)
        model_id = routing["model_id"]
        rule = routing["rule"]
        return model_id, rule

    def _call_api(self, model: str, messages: List[Dict[str,str]], params: Dict[str,Any]) -> Dict[str,Any]:
        payload = {"model": model, "messages": messages, **params}
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        response = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=payload, timeout=30)
        # Error classification reused
        if response.status_code == 429:
            retry_after = response.headers.get('retry-after', '60')
            raise Exception(f"RATE_LIMIT_EXCEEDED:Retry after {retry_after} seconds")
        elif response.status_code == 401:
            raise Exception("AUTHENTICATION_ERROR:Invalid API key")
        elif response.status_code == 403:
            raise Exception("QUOTA_EXCEEDED:API quota exceeded")
        elif response.status_code >= 500:
            raise Exception("SERVER_ERROR:Groq server error")
        response.raise_for_status()
        return response.json()

    def generate_content(self, prompt: str, system_instruction: Optional[str] = None, intent: Optional[str] = None, model_id: Optional[str] = None) -> str:
        """
        Generate content using Groq's LLaMA 3 70B model
        
        This method maintains compatibility with the Gemini interface while
        using Groq's OpenAI-compatible chat completions API.
        
        Args:
            prompt (str): User prompt/message
            system_instruction (str, optional): System instruction for the model
            
        Returns:
            str: Generated response text
            
        Raises:
            Exception: If API call fails or returns invalid response
        """
        try:
            messages = self._prepare_messages(prompt, system_instruction)
            # Routing selection
            selected_model, rule = self._select_model(messages, intent)
            if model_id:
                selected_model = model_id
            model_cfg = get_model(selected_model) or {}
            max_ctx = int(model_cfg.get("max_context_tokens", 8192))
            messages = trim_messages(messages, max_ctx - 1024)  # leave headroom for completion
            attempt_model = selected_model
            attempts = 0
            last_error = None
            while attempts < 3 and attempt_model:
                attempts += 1
                if not allow_request(attempt_model):
                    attempt_model = choose_fallback(attempt_model)
                    continue
                try:
                    logger.debug(f"Groq routed model={attempt_model} rule={rule} attempt={attempts}")
                    response_data = self._call_api(attempt_model, messages, self.default_params)
                    record_success(attempt_model)
                    break
                except Exception as e:  # classify recoverable
                    record_failure(attempt_model)
                    last_error = e
                    attempt_model = choose_fallback(attempt_model)
                    continue
            else:
                # exhausted
                if last_error:
                    raise last_error
                raise Exception("MODEL_ROUTING_FAILED:No model succeeded")
            
            # Extract generated text
            if response_data and "choices" in response_data and len(response_data["choices"]) > 0:
                content = response_data["choices"][0]["message"]["content"]
                logger.debug(f"Groq API response generated: {len(content)} characters")
                return content
            else:
                raise Exception("No choices in Groq API response")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Groq API request failed: {str(e)}")
            raise Exception(f"Groq API request failed: {str(e)}")
        except Exception as e:
            logger.error(f"Groq content generation failed: {str(e)}")
            raise
    
    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """
        Direct chat completions API call
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            **kwargs: Additional parameters to override defaults
            
        Returns:
            dict: Full API response
        """
        try:
            # Merge parameters
            params = {**self.default_params, **kwargs}
            
            # Prepare request payload
            payload = {
                "model": self.model,
                "messages": messages,
                **params
            }
            
            # Make API request
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            # Enhanced error handling
            if response.status_code == 429:
                retry_after = response.headers.get('retry-after', '60')
                raise Exception(f"RATE_LIMIT_EXCEEDED:Retry after {retry_after} seconds")
            elif response.status_code == 401:
                raise Exception("AUTHENTICATION_ERROR:Invalid API key")
            elif response.status_code == 403:
                raise Exception("QUOTA_EXCEEDED:API quota exceeded")
            elif response.status_code >= 500:
                raise Exception("SERVER_ERROR:Groq server error")
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Groq chat completion failed: {str(e)}")
            raise Exception(f"Groq chat completion failed: {str(e)}")


# Create a mock response object to maintain compatibility with Gemini interface
class GroqResponse:
    """Mock response object to maintain compatibility with Gemini interface"""
    
    def __init__(self, text: str):
        self.text = text


# Initialize global Groq client
try:
    groq_client = GroqClient()
    logger.info("✅ Global Groq client initialized")
except Exception as e:
    logger.error(f"❌ Failed to initialize Groq client: {str(e)}")
    groq_client = None


def generate_with_groq(prompt: str, system_instruction: Optional[str] = None) -> GroqResponse:
    """
    Convenience function to generate content with Groq
    
    This function provides a Gemini-compatible interface for easy migration.
    
    Args:
        prompt (str): User prompt
        system_instruction (str, optional): System instruction
        
    Returns:
        GroqResponse: Response object with .text property
    """
    if not groq_client:
        raise Exception("Groq client not initialized")
    
    content = groq_client.generate_content(prompt, system_instruction)
    return GroqResponse(content)
