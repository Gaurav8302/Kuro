#!/usr/bin/env python3
"""
Comprehensive Memory System Test

Tests the improved memory system for better context management
and inter-session memory retention.
"""

import asyncio
import uuid
from datetime import datetime
from memory.chat_manager import chat_with_memory
from memory.user_profile import set_user_name
from memory.chat_database import save_chat_to_db, get_chat_by_session, create_new_session
from memory.rolling_memory import rolling_memory_manager
import time

def test_session_memory():
    """Test short-term memory within a single session"""
    print("🧠 Testing Session Memory (Short-term Context)")
    
    test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    session_id = create_new_session(test_user_id)
    
    # Set user name
    set_user_name(test_user_id, "TestUser")
    
    # Conversation 1: Establish context
    print("\n1. Establishing context about favorite programming language...")
    response1 = chat_with_memory(
        test_user_id, 
        "My favorite programming language is Python because it's so versatile",
        session_id
    )
    print(f"Response 1: {response1[:100]}...")
    
    # Small delay to ensure timestamp ordering
    time.sleep(1)
    
    # Conversation 2: Reference should be maintained
    print("\n2. Testing if AI remembers the programming language...")
    response2 = chat_with_memory(
        test_user_id,
        "What programming language did I just mention?",
        session_id
    )
    print(f"Response 2: {response2[:100]}...")
    
    # Conversation 3: Building on context
    print("\n3. Building on the context with a follow-up...")
    response3 = chat_with_memory(
        test_user_id,
        "Can you recommend some advanced Python libraries for that reason?",
        session_id
    )
    print(f"Response 3: {response3[:100]}...")
    
    # Conversation 4: Testing pronoun resolution
    print("\n4. Testing pronoun resolution...")
    response4 = chat_with_memory(
        test_user_id,
        "Which one would be best for data science?",
        session_id
    )
    print(f"Response 4: {response4[:100]}...")
    
    # Check if responses show memory
    memory_indicators = ["python", "programming", "language", "mentioned", "said", "told"]
    response2_lower = response2.lower()
    
    if any(indicator in response2_lower for indicator in memory_indicators):
        print("✅ Session memory working - AI referenced the programming language")
    else:
        print("❌ Session memory issue - AI didn't reference the programming language")
    
    return session_id, test_user_id

def test_inter_session_memory():
    """Test long-term memory across different sessions"""
    print("\n🔄 Testing Inter-Session Memory (Long-term Context)")
    
    test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    
    # Session 1: Establish preferences
    session1_id = create_new_session(test_user_id)
    set_user_name(test_user_id, "MemoryTestUser")
    
    print("\n1. Session 1 - Establishing user preferences...")
    response1 = chat_with_memory(
        test_user_id,
        "I love machine learning and I'm working on a computer vision project with OpenCV",
        session1_id
    )
    print(f"Session 1 Response: {response1[:100]}...")
    
    # Trigger rolling memory summarization
    rolling_memory_manager.schedule_summarization(test_user_id, session1_id)
    time.sleep(2)  # Allow summarization to complete
    
    # Session 2: Test memory retention
    session2_id = create_new_session(test_user_id)
    
    print("\n2. Session 2 - Testing if AI remembers across sessions...")
    response2 = chat_with_memory(
        test_user_id,
        "Hi, do you remember what I'm working on?",
        session2_id
    )
    print(f"Session 2 Response: {response2[:100]}...")
    
    # Check for memory retention indicators
    memory_indicators = ["machine learning", "computer vision", "opencv", "project", "working", "remember"]
    response2_lower = response2.lower()
    
    if any(indicator in response2_lower for indicator in memory_indicators):
        print("✅ Inter-session memory working - AI remembered across sessions")
    else:
        print("❌ Inter-session memory issue - AI didn't remember across sessions")
    
    return session1_id, session2_id, test_user_id

def test_context_building():
    """Test context building with multiple conversation turns"""
    print("\n🏗️ Testing Context Building")
    
    test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    session_id = create_new_session(test_user_id)
    set_user_name(test_user_id, "ContextTestUser")
    
    conversations = [
        "I'm planning a trip to Japan next month",
        "I'm interested in both modern cities and traditional temples",
        "My budget is around $3000 for the whole trip",
        "I'll be there for 10 days",
        "What would you recommend for someone with my interests and budget?"
    ]
    
    responses = []
    for i, message in enumerate(conversations):
        print(f"\n{i+1}. User: {message}")
        response = chat_with_memory(test_user_id, message, session_id)
        responses.append(response)
        print(f"   AI: {response[:100]}...")
        time.sleep(1)  # Small delay between messages
    
    # Final response should reference multiple previous contexts
    final_response = responses[-1].lower()
    context_indicators = ["japan", "budget", "3000", "10 days", "temples", "cities", "trip"]
    
    found_indicators = [indicator for indicator in context_indicators if indicator in final_response]
    
    if len(found_indicators) >= 3:
        print(f"✅ Context building working - Found {len(found_indicators)} context references")
    else:
        print(f"❌ Context building issue - Only found {len(found_indicators)} context references")
    
    return session_id, test_user_id

def test_memory_recall():
    """Test memory recall functionality"""
    print("\n🔍 Testing Memory Recall")
    
    test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    session_id = create_new_session(test_user_id)
    set_user_name(test_user_id, "RecallTestUser")
    
    # Store some memorable information
    setup_messages = [
        "My name is Alex and I work as a software engineer at Google",
        "I have 5 years of experience in Python and machine learning",
        "I'm currently working on a recommendation system project"
    ]
    
    for message in setup_messages:
        chat_with_memory(test_user_id, message, session_id)
        time.sleep(1)
    
    # Test recall
    recall_test = chat_with_memory(
        test_user_id,
        "Can you tell me what you remember about me?",
        session_id
    )
    
    recall_indicators = ["alex", "software engineer", "google", "python", "machine learning", "recommendation"]
    recall_lower = recall_test.lower()
    
    found_recall = [indicator for indicator in recall_indicators if indicator in recall_lower]
    
    if len(found_recall) >= 3:
        print(f"✅ Memory recall working - Recalled {len(found_recall)} key facts")
        print(f"   Recalled: {found_recall}")
    else:
        print(f"❌ Memory recall issue - Only recalled {len(found_recall)} facts")
    
    return session_id, test_user_id

async def main():
    """Run all memory tests"""
    print("🚀 Starting Comprehensive Memory System Tests")
    print("=" * 60)
    
    try:
        # Test 1: Session memory
        session_id1, user_id1 = test_session_memory()
        
        # Test 2: Inter-session memory
        session1_id, session2_id, user_id2 = test_inter_session_memory()
        
        # Test 3: Context building
        session_id3, user_id3 = test_context_building()
        
        # Test 4: Memory recall
        session_id4, user_id4 = test_memory_recall()
        
        print("\n" + "=" * 60)
        print("🎯 Memory System Test Summary")
        print("All tests completed. Check individual results above.")
        print("If any tests failed, the memory system needs further improvements.")
        
    except Exception as e:
        print(f"❌ Test error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
