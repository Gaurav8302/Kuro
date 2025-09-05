#!/usr/bin/env python3
"""Quick deployment verification script to test basic functionality."""

import requests
import sys
import os

def test_health():
    """Test basic health endpoint."""
    try:
        url = os.getenv('RENDER_EXTERNAL_URL', 'http://localhost:8000')
        response = requests.get(f"{url}/healthz", timeout=10)
        print(f"✅ Health check: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Health check failed: {str(e)}")
        return False

def test_ping():
    """Test ping endpoint."""
    try:
        url = os.getenv('RENDER_EXTERNAL_URL', 'http://localhost:8000')
        response = requests.get(f"{url}/ping", timeout=10)
        print(f"✅ Ping test: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Ping test failed: {str(e)}")
        return False

def test_routing_without_embeddings():
    """Test that routing works even without embeddings."""
    try:
        # This would normally be an internal test, but we can verify
        # the imports work
        import sys
        sys.path.append('/opt/render/project/src')
        from routing.model_router import route_to_best_model
        
        # Test basic routing
        result = route_to_best_model(
            message="Hello, how are you?",
            context_tokens=10
        )
        print(f"✅ Routing test: {result['selected_model']}")
        return True
    except Exception as e:
        print(f"❌ Routing test failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Running deployment verification...")
    
    tests = [
        test_health,
        test_ping,
        # test_routing_without_embeddings,  # Skip for external test
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n📊 Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 Deployment verification successful!")
        sys.exit(0)
    else:
        print("⚠️ Some tests failed, but basic functionality may still work")
        sys.exit(1)
