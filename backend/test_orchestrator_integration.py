"""
Test script for the Orchestrator integration

This script tests the orchestrator functionality and its integration
with the ChatManager.

To run: python test_orchestrator_integration.py
"""

import os
import sys
import asyncio
import logging
from typing import Dict, Any

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_orchestrator_standalone():
    """Test the orchestrator module directly"""
    print("\n🔍 Testing Orchestrator Standalone...")
    
    try:
        from orchestrator import orchestrate
        
        test_queries = [
            "solve x^2 + 5x + 6 = 0",
            "write a Python function to reverse a string",
            "what do you remember about our last conversation?",
            "hello, how are you doing today?",
            "calculate the derivative of sin(x^2)"
        ]
        
        for query in test_queries:
            print(f"\n📝 Query: {query}")
            try:
                result = await orchestrate(query, {"user_id": "test_user", "session_id": "test_session"})
                print(f"✅ Task: {result['task']}")
                print(f"🎯 Confidence: {result['confidence']}")
                print(f"📋 Instructions: {result['instructions']}")
                print(f"🛠️ Tools: {result['tools']}")
                print(f"📄 Format: {result['expected_response_format']}")
                print(f"📝 Expanded prompt: {result['expanded_prompt'][:100]}...")
            except Exception as e:
                print(f"❌ Error: {str(e)}")
                
    except ImportError as e:
        print(f"❌ Cannot import orchestrator: {str(e)}")
    except Exception as e:
        print(f"❌ Orchestrator test failed: {str(e)}")

def test_chat_manager_integration():
    """Test the ChatManager integration with orchestrator"""
    print("\n🔍 Testing ChatManager Integration...")
    
    try:
        from memory.chat_manager import ChatManager
        
        # Check if orchestrator is available
        from memory.chat_manager import ORCHESTRATOR_AVAILABLE
        print(f"📡 Orchestrator available: {ORCHESTRATOR_AVAILABLE}")
        
        # Create chat manager instance
        chat_manager = ChatManager()
        print("✅ ChatManager initialized successfully")
        
        # Test a simple chat (without actually calling external APIs)
        test_user_id = "test_user_123"
        test_session_id = "test_session_456"
        test_message = "Hello, can you help me solve a math problem?"
        
        print(f"📝 Test message: {test_message}")
        print("⏳ Processing with orchestrator integration...")
        
        # Note: This will fail without proper API keys, but we can see if the integration is working
        try:
            response = chat_manager.chat_with_memory(
                user_id=test_user_id,
                message=test_message,
                session_id=test_session_id
            )
            print(f"✅ Response generated: {response[:100]}...")
        except Exception as e:
            if "OPENROUTER_API_KEY" in str(e) or "API" in str(e):
                print(f"⚠️ Expected API error (no keys): {str(e)}")
            else:
                print(f"❌ Unexpected error: {str(e)}")
                
    except Exception as e:
        print(f"❌ ChatManager integration test failed: {str(e)}")

def main():
    """Main test function"""
    print("🚀 Starting Orchestrator Integration Tests")
    print("=" * 50)
    
    # Check environment
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("⚠️ OPENROUTER_API_KEY not set - some tests may fail")
    else:
        print("✅ OPENROUTER_API_KEY found")
    
    # Test orchestrator standalone
    asyncio.run(test_orchestrator_standalone())
    
    # Test chat manager integration
    test_chat_manager_integration()
    
    print("\n" + "=" * 50)
    print("🏁 Tests completed!")

if __name__ == "__main__":
    main()
