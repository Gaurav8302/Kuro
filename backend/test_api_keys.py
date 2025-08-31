#!/usr/bin/env python3
"""
Quick API key test script to diagnose deployment issues
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_api_keys():
    """Test if all required API keys are available"""
    print("🔍 Testing API Keys Configuration...")
    print("=" * 50)
    
    # Required API keys
    api_keys = {
        "GROQ_API_KEY": os.getenv("GROQ_API_KEY"),
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
        "OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY"),
        "CLERK_SECRET_KEY": os.getenv("CLERK_SECRET_KEY"),
        "MONGODB_URI": os.getenv("MONGODB_URI"),
        "PINECONE_API_KEY": os.getenv("PINECONE_API_KEY"),
    }
    
    missing_keys = []
    for key, value in api_keys.items():
        if value:
            print(f"✅ {key}: Present (length: {len(value)})")
        else:
            print(f"❌ {key}: MISSING")
            missing_keys.append(key)
    
    print("=" * 50)
    
    if missing_keys:
        print(f"🚨 MISSING KEYS: {', '.join(missing_keys)}")
        print("📝 These keys need to be set in your Render environment variables")
        return False
    else:
        print("✅ All API keys are present!")
        return True

def test_client_initialization():
    """Test if clients can be initialized"""
    print("\n🔧 Testing Client Initialization...")
    print("=" * 50)
    
    # Test Groq client
    try:
        from utils.groq_client import GroqClient
        groq_client = GroqClient()
        print("✅ Groq Client: Initialized successfully")
    except Exception as e:
        print(f"❌ Groq Client: Failed - {str(e)}")
    
    # Test OpenRouter client
    try:
        from utils.openrouter_client import OpenRouterClient
        openrouter_client = OpenRouterClient()
        print("✅ OpenRouter Client: Initialized successfully")
    except Exception as e:
        print(f"❌ OpenRouter Client: Failed - {str(e)}")
    
    # Test memory/vector DB
    try:
        from memory.ultra_lightweight_memory import ultra_lightweight_memory_manager
        print("✅ Memory Manager: Initialized successfully")
    except Exception as e:
        print(f"❌ Memory Manager: Failed - {str(e)}")

def main():
    """Main diagnostic function"""
    print("🚀 Kuro AI - API Diagnostics")
    print("=" * 50)
    
    # Test API keys
    keys_ok = test_api_keys()
    
    # Test client initialization
    test_client_initialization()
    
    print("\n" + "=" * 50)
    if keys_ok:
        print("🎉 Diagnostics complete! Check client initialization results above.")
    else:
        print("🚨 Fix missing API keys first, then re-run diagnostics.")
    
    return 0 if keys_ok else 1

if __name__ == "__main__":
    sys.exit(main())
