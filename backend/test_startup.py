#!/usr/bin/env python3
"""
Quick startup test for the chatbot application
"""

import os
import sys

def test_imports():
    """Test all critical imports"""
    print("🧪 Testing imports...")
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ Environment loading")
        
        import fastapi
        print("✅ FastAPI")
        
        import uvicorn
        print("✅ Uvicorn")
        
        import pymongo
        print("✅ PyMongo")
        
        import pinecone
        print("✅ Pinecone")
        
        import google.generativeai
        print("✅ Google Generative AI")
        
        # Test our custom modules
        from memory.ultra_lightweight_memory import ultra_lightweight_memory_manager
        print("✅ Ultra-lightweight memory manager")
        
        from memory.chat_manager_v2 import chat_with_memory
        print("✅ Chat manager v2")
        
        from memory.chat_database import get_sessions_by_user
        print("✅ Chat database")
        
        print("🎉 All imports successful!")
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_app_creation():
    """Test FastAPI app creation"""
    print("\n🚀 Testing app creation...")
    
    try:
        from chatbot import app
        print("✅ FastAPI app created successfully")
        return True
        
    except Exception as e:
        print(f"❌ App creation failed: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Chatbot Startup Test")
    print("=" * 40)
    
    # Test imports
    imports_ok = test_imports()
    
    if imports_ok:
        # Test app creation
        app_ok = test_app_creation()
        
        if app_ok:
            print("\n🎉 All tests passed! App should start successfully.")
            sys.exit(0)
        else:
            print("\n❌ App creation failed.")
            sys.exit(1)
    else:
        print("\n❌ Import tests failed.")
        sys.exit(1)
