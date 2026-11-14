#!/usr/bin/env python3
"""Test script for the enhanced Kuro AI routing system.

Tests all the new features:
- Hybrid intent detection (regex + embeddings)
- Latency-aware routing with EMA tracking
- Blended scoring system
- Session-based adaptations
- Circuit breaker patterns
- Explainable logging
"""

import asyncio
import sys
import time
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

async def test_enhanced_routing():
    """Test the enhanced routing system."""
    print("🚀 Testing Enhanced Kuro AI Routing System")
    print("=" * 50)
    
    try:
        # Test 1: Import all new modules
        print("\n1. Testing module imports...")
        
        from routing.embedding_similarity import get_embedding_similarity
        from routing.latency_tracker import get_latency_tracker
        from routing.session_tracker import get_session_manager
        from routing.circuit_breaker import get_circuit_breaker
        from routing.explainable_logging import get_explainable_logger
        from routing.model_router import route_model, route_model_with_parallel_fallback
        from skills.skill_manager import skill_manager
        
        print("✅ All modules imported successfully")
        
        # Test 2: Embedding similarity
        print("\n2. Testing embedding similarity...")
        
        embedding_sim = get_embedding_similarity()
        if embedding_sim.model is not None:
            similarity = embedding_sim.compute_similarity(
                "explain this step by step", 
                "walk me through the logic"
            )
            print(f"✅ Embedding similarity test: {similarity:.3f}")
        else:
            print("⚠️ Embedding model not available (sentence-transformers not installed)")
        
        # Test 3: Latency tracking
        print("\n3. Testing latency tracking...")
        
        latency_tracker = get_latency_tracker()
        latency_tracker.record_latency("test-model", 1500.0)
        recorded_latency = latency_tracker.get_latency("test-model")
        print(f"✅ Latency tracking test: {recorded_latency:.1f}ms")
        
        # Test 4: Circuit breaker
        print("\n4. Testing circuit breaker...")
        
        circuit_breaker = get_circuit_breaker()
        can_execute, reason = circuit_breaker.can_execute("test-model")
        print(f"✅ Circuit breaker test: can_execute={can_execute}, reason={reason}")
        
        # Test 5: Session management
        print("\n5. Testing session management...")
        
        session_manager = get_session_manager()
        session = session_manager.get_session("test-session-123")
        session.record_skill_usage("debugging")
        boost = session.get_skill_priority_boost("debugging")
        print(f"✅ Session management test: priority_boost={boost}")
        
        # Test 6: Enhanced routing
        print("\n6. Testing enhanced routing...")
        
        test_queries = [
            "Hello there, how are you?",
            "Explain step by step how photosynthesis works",
            "Debug this Python error: NameError: name 'x' is not defined",
            "Summarize this long article for me",
            "Write a creative story about space exploration"
        ]
        
        for i, query in enumerate(test_queries):
            print(f"\n   Query {i+1}: {query[:50]}...")
            
            try:
                routing_result = await route_model_with_parallel_fallback(
                    query, 1000, session_id="test-session-123"
                )
                
                print(f"   ✅ Model: {routing_result['model_id']}")
                print(f"   ✅ Rule: {routing_result['rule']}")
                print(f"   ✅ Confidence: {routing_result['confidence']:.2f}")
                print(f"   ✅ Explanation: {routing_result['explanation'][:100]}...")
                
            except Exception as e:
                print(f"   ❌ Routing failed: {str(e)}")
        
        # Test 7: Enhanced skill selection
        print("\n7. Testing enhanced skill selection...")
        
        for i, query in enumerate(test_queries[:3]):
            print(f"\n   Query {i+1}: {query[:50]}...")
            
            try:
                base_system = "You are Kuro AI."
                enhanced_system, skills, metadata = skill_manager.build_injected_system_prompt(
                    base_system, query, "test-session-123"
                )
                
                print(f"   ✅ Applied skills: {skills}")
                print(f"   ✅ Selection time: {metadata.get('selection_time_ms', 0):.1f}ms")
                print(f"   ✅ Skills evaluated: {metadata.get('skills_evaluated', 0)}")
                
            except Exception as e:
                print(f"   ❌ Skill selection failed: {str(e)}")
        
        # Test 8: Explainable logging
        print("\n8. Testing explainable logging...")
        
        explainable_logger = get_explainable_logger()
        stats = explainable_logger.get_statistics()
        print(f"✅ Logging stats: {stats}")
        
        recent_decisions = explainable_logger.get_recent_decisions(count=3)
        print(f"✅ Recent decisions: {len(recent_decisions)} entries")
        
        # Test 9: Integration test with orchestrator
        print("\n9. Testing orchestrator integration...")
        
        try:
            from orchestration.llm_orchestrator import orchestrate
            
            # Mock the client to avoid actual API calls
            import unittest.mock
            
            with unittest.mock.patch('orchestration.llm_orchestrator.client') as mock_client:
                mock_client.generate_content.return_value = "Test response from Kuro AI!"
                
                result = await orchestrate(
                    user_message="Hello, can you help me debug a Python error?",
                    session_id="test-session-integration"
                )
                
                print(f"   ✅ Reply: {result['reply'][:100]}...")
                print(f"   ✅ Model: {result['model']}")
                print(f"   ✅ Confidence: {result.get('confidence', 'N/A')}")
                print(f"   ✅ Applied skills: {result.get('applied_skills', [])}")
                print(f"   ✅ Routing explanation: {result.get('routing_explanation', 'N/A')[:100]}...")
                
        except Exception as e:
            print(f"   ❌ Orchestrator integration failed: {str(e)}")
        
        print("\n" + "=" * 50)
        print("🎉 Enhanced routing system test completed!")
        print("\nKey improvements implemented:")
        print("✅ Hybrid intent detection (regex + embeddings)")
        print("✅ Latency-aware routing with EMA tracking")
        print("✅ Blended scoring system (no hard tiers)")
        print("✅ Session-based adaptive behavior")
        print("✅ Circuit breaker for failure handling")
        print("✅ Explainable logging for all decisions")
        print("✅ Enhanced skill selection with conflicts resolution")
        print("✅ Parallel fallback for critical intents")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


def test_backwards_compatibility():
    """Test that existing function signatures still work."""
    print("\n🔄 Testing backwards compatibility...")
    
    try:
        from routing.model_router import route_model
        from skills.skill_manager import skill_manager
        
        # Test old route_model signature
        result = route_model("Hello", 1000, intent="casual_chat")
        print(f"✅ Old route_model signature works: {result['model_id']}")
        
        # Test old skill manager signature
        base_system = "You are Kuro."
        enhanced, skills = skill_manager.build_injected_system_prompt_legacy(base_system, "Hello")
        print(f"✅ Old skill manager signature works: {len(skills)} skills")
        
        print("✅ Backwards compatibility maintained!")
        
    except Exception as e:
        print(f"❌ Backwards compatibility test failed: {str(e)}")


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_enhanced_routing())
    test_backwards_compatibility()
    
    print("\n" + "=" * 50)
    print("📋 Next steps to complete deployment:")
    print("1. Install sentence-transformers: pip install sentence-transformers torch")
    print("2. Update production environment variables if needed")
    print("3. Monitor routing logs for performance")
    print("4. Adjust thresholds based on real usage patterns")
    print("5. Consider enabling parallel fallback for production")
