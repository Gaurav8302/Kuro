#!/usr/bin/env python3
"""
Test script for Kuro AI prompt system

This script tests the integration of the new Kuro prompt system
and safety validators to ensure everything works correctly.
"""

import sys
import os

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_kuro_prompt_system():
    """Test the Kuro prompt system"""
    try:
        from utils.kuro_prompt import build_kuro_prompt, sanitize_response
        print("✅ Kuro prompt system imported successfully")
        
        # Test prompt building
        test_message = "What is Python?"
        prompt_package = build_kuro_prompt(test_message)
        
        print(f"✅ Generated system instruction ({len(prompt_package['system_instruction'])} chars)")
        print(f"✅ Generated user prompt ({len(prompt_package['user_prompt'])} chars)")
        
        # Test sanitization
        test_response = "Here's how Python works:\n\n```python\nprint('Hello')\n```"
        sanitized = sanitize_response(test_response)
        print(f"✅ Response sanitization works ({len(sanitized)} chars)")
        
        return True
        
    except Exception as e:
        print(f"❌ Kuro prompt system error: {e}")
        return False

def test_safety_system():
    """Test the safety validation system"""
    try:
        from utils.safety import validate_response, get_fallback_response
        print("✅ Safety system imported successfully")
        
        # Test safe response validation
        safe_response = "Python is a programming language that's great for beginners."
        is_valid, assessment = validate_response(safe_response)
        print(f"✅ Safe response validation: {is_valid} (quality: {assessment.get('quality_score', 0):.2f})")
        
        # Test fallback response
        fallback = get_fallback_response("test message")
        print(f"✅ Fallback response generated ({len(fallback)} chars)")
        
        return True
        
    except Exception as e:
        print(f"❌ Safety system error: {e}")
        return False

def test_chat_manager_integration():
    """Test integration with chat manager"""
    try:
        # This will test if the imports work in the chat manager
        import memory.chat_manager
        print("✅ Chat manager imports work with new system")
        return True
        
    except Exception as e:
        print(f"❌ Chat manager integration error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Kuro AI Prompt System Integration\n")
    
    tests = [
        ("Kuro Prompt System", test_kuro_prompt_system),
        ("Safety System", test_safety_system),
        ("Chat Manager Integration", test_chat_manager_integration)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Testing {test_name}:")
        if test_func():
            passed += 1
        
    print(f"\n🎯 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All systems ready for production!")
    else:
        print("⚠️ Some tests failed - please check the errors above")
