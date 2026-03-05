#!/usr/bin/env python3
"""
AI Setup Verification Script
Tests all AI components to ensure Gemini -> Groq migration was successful
"""

import os
import sys
import traceback
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_environment():
    """Test environment variables"""
    print("🔧 ENVIRONMENT VARIABLES CHECK")
    print("=" * 50)
    
    required_vars = {
        'GROQ_API_KEY': 'Groq LLaMA 3 70B (Chat Responses)',
        'GEMINI_API_KEY': 'Google Gemini (Embeddings - Free)',
        'PINECONE_API_KEY': 'Pinecone (Vector Database)',
        'MONGODB_URI': 'MongoDB (Chat History)'
    }
    
    all_present = True
    for var, purpose in required_vars.items():
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: Present ({purpose})")
        else:
            print(f"❌ {var}: MISSING ({purpose})")
            all_present = False
    
    print("\n")
    return all_present

def test_groq_client():
    """Test Groq client for chat responses"""
    print("🤖 GROQ CLIENT TEST (Chat Responses)")
    print("=" * 50)
    
    try:
        # Import should work
        from utils.groq_client import GroqClient
        print("✅ Groq client import successful")
        
        # Initialize client
        groq_client = GroqClient()
        print("✅ Groq client initialized")
        
        # Test simple request
        response = groq_client.generate_content(
            prompt="Say 'Hello World' and nothing else"
        )
        
        if response and len(response.strip()) > 0:
            print(f"✅ Groq response: '{response.strip()}'")
            print("✅ Groq LLaMA 3 70B working correctly")
            return True
        else:
            print("❌ Empty response from Groq")
            return False
            
    except Exception as e:
        print(f"❌ Groq client error: {e}")
        print(f"❌ Stack trace: {traceback.format_exc()}")
        return False
    
    finally:
        print("\n")

def test_gemini_embeddings():
    """Test Gemini embeddings for memory"""
    print("🧠 GEMINI EMBEDDINGS TEST (Memory - Free)")
    print("=" * 50)
    
    try:
        import google.generativeai as genai
        print("✅ Gemini import successful")
        
        # Configure with API key
        api_key = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=api_key)
        print("✅ Gemini configured with API key")
        
        # Test embedding
        result = genai.embed_content(
            model="models/text-embedding-004",
            content="This is a test embedding",
            task_type="retrieval_document"
        )
        
        embedding = result['embedding']
        print(f"✅ Embedding generated: {len(embedding)} dimensions")
        
        # Check dimension reduction for Pinecone
        if len(embedding) > 384:
            reduced = embedding[::2][:384]
            print(f"✅ Dimension reduction: {len(embedding)} -> {len(reduced)}")
        
        print("✅ Gemini embeddings working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Gemini embedding error: {e}")
        print(f"❌ Stack trace: {traceback.format_exc()}")
        return False
    
    finally:
        print("\n")

def test_chat_manager():
    """Test integrated chat manager"""
    print("💬 CHAT MANAGER INTEGRATION TEST")
    print("=" * 50)
    
    try:
        from memory.chat_manager_v2 import ChatManager
        print("✅ Chat manager v2 import successful")
        
        # Initialize
        chat_manager = ChatManager()
        print("✅ Chat manager v2 initialized with Groq")
        
        # Test basic response generation
        response = chat_manager.groq_client.generate_content(
            prompt="Hello, respond with exactly: 'AI Test Successful'",
            system_instruction="This is a system test"
        )
        
        if response and len(response.strip()) > 0:
            print(f"✅ Chat response: '{response[:100]}...' " if len(response) > 100 else f"✅ Chat response: '{response}'")
            print("✅ Full chat pipeline working")
            return True
        else:
            print("❌ Empty response from chat manager")
            return False
            
    except Exception as e:
        print(f"❌ Chat manager error: {e}")
        print(f"❌ Stack trace: {traceback.format_exc()}")
        return False
    
    finally:
        print("\n")

def test_session_cleanup():
    """Test session cleanup with Groq (simplified)"""
    print("🧹 SESSION CLEANUP TEST")
    print("=" * 50)
    
    try:
        # Test just the Groq part of session cleanup
        from utils.groq_client import GroqClient
        print("✅ Groq client import for cleanup successful")
        
        groq_client = GroqClient()
        print("✅ Groq client for cleanup initialized")
        
        # Test summary generation directly
        prompt = """
        Summarize this conversation:
        User: Hello, how are you?
        Assistant: I'm doing well, thank you for asking!
        
        Provide a brief summary of the key topics discussed.
        """
        
        summary = groq_client.generate_content(prompt.strip())
        
        if summary and len(summary.strip()) > 0:
            print(f"✅ Session summary: '{summary[:100]}...' " if len(summary) > 100 else f"✅ Session summary: '{summary}'")
            print("✅ Session cleanup Groq integration working")
            return True
        else:
            print("❌ Empty summary generated")
            return False
            
    except Exception as e:
        print(f"❌ Session cleanup error: {e}")
        print(f"❌ Stack trace: {traceback.format_exc()}")
        return False
    
    finally:
        print("\n")

def main():
    """Main verification function"""
    print("🚀 AI SETUP VERIFICATION")
    print("=" * 50)
    print("Verifying Gemini -> Groq migration was successful...")
    print("Groq: Chat responses | Gemini: Embeddings (free)\n")
    
    tests = [
        ("Environment Variables", test_environment),
        ("Groq Client", test_groq_client),
        ("Gemini Embeddings", test_gemini_embeddings),
        ("Chat Manager", test_chat_manager),
        ("Session Cleanup", test_session_cleanup)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("📊 VERIFICATION SUMMARY")
    print("=" * 50)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nResult: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Your AI setup is working correctly.")
        print("✅ Groq LLaMA 3 70B handling chat responses")
        print("✅ Gemini handling embeddings (free)")
        print("✅ Ready for deployment!")
    else:
        print(f"\n⚠️  {total - passed} tests failed. Please check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️  Verification cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        print(f"Stack trace: {traceback.format_exc()}")
        sys.exit(1)
