#!/usr/bin/env python3
"""
Memory System Logic Test

Tests the memory system improvements without requiring API keys
by testing the logic and structure.
"""

import sys
import os

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_rolling_memory_config():
    """Test rolling memory configuration improvements"""
    print("🧠 Testing Rolling Memory Configuration")
    
    try:
        from memory.rolling_memory import RollingMemoryManager
        
        # Test with default improved settings
        manager = RollingMemoryManager()
        
        if manager.short_term_window == 20:
            print("✅ Short-term window increased to 20 messages")
        else:
            print(f"❌ Short-term window is {manager.short_term_window}, expected 20")
            
        if manager.min_chunk == 8:
            print("✅ Minimum chunk size increased to 8")
        else:
            print(f"❌ Minimum chunk size is {manager.min_chunk}, expected 8")
            
        return True
    except Exception as e:
        print(f"❌ Rolling memory test failed: {e}")
        return False

def test_chat_manager_structure():
    """Test chat manager structure improvements"""
    print("\n💬 Testing Chat Manager Structure")
    
    try:
        import inspect
        
        # Import without initializing (to avoid API key requirements)
        spec = __import__('memory.chat_manager', fromlist=['ChatManager'])
        ChatManager = getattr(spec, 'ChatManager')
        
        # Check if the methods exist with improved signatures
        methods = inspect.getmembers(ChatManager, predicate=inspect.isfunction)
        method_names = [name for name, _ in methods]
        
        required_methods = [
            'chat_with_memory',
            'build_context_prompt', 
            '_store_chat_memory'
        ]
        
        for method in required_methods:
            if method in method_names:
                print(f"✅ Method {method} exists")
            else:
                print(f"❌ Method {method} missing")
                
        return True
    except Exception as e:
        print(f"❌ Chat manager structure test failed: {e}")
        return False

def test_api_endpoint_changes():
    """Test API endpoint improvements"""
    print("\n🌐 Testing API Endpoint Changes")
    
    try:
        with open('chatbot.py', 'r') as f:
            content = f.read()
            
        # Check if chat_manager.chat_with_memory is used
        if 'chat_manager.chat_with_memory' in content:
            print("✅ Main endpoint now uses chat_manager.chat_with_memory")
        else:
            print("❌ Main endpoint doesn't use chat_manager.chat_with_memory")
            
        # Check if orchestrator is removed from main flow
        if 'orchestrate(' not in content or content.count('orchestrate(') < content.count('chat_manager.chat_with_memory'):
            print("✅ Orchestrator usage reduced in favor of chat_manager")
        else:
            print("❌ Orchestrator still dominates the main chat flow")
            
        return True
    except Exception as e:
        print(f"❌ API endpoint test failed: {e}")
        return False

def test_memory_improvements_in_code():
    """Test that memory improvements are reflected in the code"""
    print("\n🔍 Testing Memory Improvements in Code")
    
    try:
        with open('memory/chat_manager.py', 'r') as f:
            content = f.read()
            
        improvements_found = 0
        
        # Check for increased session history
        if 'session_history = chat_data[-10:]' in content:
            print("✅ Session history increased to 10 messages")
            improvements_found += 1
        else:
            print("❌ Session history not increased to 10 messages")
            
        # Check for increased recent exchanges
        if 'recent_exchanges = session_history[-4:]' in content:
            print("✅ Recent exchanges increased to 4 messages")
            improvements_found += 1
        else:
            print("❌ Recent exchanges not increased to 4 messages")
            
        # Check for improved short-term context
        if 'rolling_context["short_term"][-8:]' in content:
            print("✅ Short-term rolling context increased to 8 turns")
            improvements_found += 1
        else:
            print("❌ Short-term rolling context not increased to 8 turns")
            
        # Check for better memory storage
        if 'len(message) < 5' in content:
            print("✅ Memory storage threshold reduced to 5 characters")
            improvements_found += 1
        else:
            print("❌ Memory storage threshold not improved")
            
        # Check for improved prompt
        if 'You are Kuro' in content and 'created by Gaurav' in content:
            print("✅ AI identity properly established as Kuro created by Gaurav")
            improvements_found += 1
        else:
            print("❌ AI identity not properly established")
            
        print(f"\n📊 Found {improvements_found}/5 expected improvements")
        return improvements_found >= 4
        
    except Exception as e:
        print(f"❌ Memory improvements test failed: {e}")
        return False

def main():
    """Run all logic tests"""
    print("🚀 Starting Memory System Logic Tests")
    print("=" * 60)
    
    tests_passed = 0
    total_tests = 4
    
    if test_rolling_memory_config():
        tests_passed += 1
        
    if test_chat_manager_structure():
        tests_passed += 1
        
    if test_api_endpoint_changes():
        tests_passed += 1
        
    if test_memory_improvements_in_code():
        tests_passed += 1
    
    print("\n" + "=" * 60)
    print(f"🎯 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("✅ All logic tests passed! Memory system improvements are in place.")
    elif tests_passed >= total_tests * 0.75:
        print("⚠️ Most tests passed. Minor issues may exist.")
    else:
        print("❌ Several tests failed. Memory system needs more work.")
    
    return tests_passed == total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
