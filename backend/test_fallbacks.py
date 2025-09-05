#!/usr/bin/env python3
"""Test fallback routing logic"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from config.config_loader import get_model
from reliability.fallback_router import choose_fallback

def test_fallback_chain():
    print("🔧 Testing Model Fallback Chain")
    print("=" * 50)
    
    # Test starting from llama-3.1-8B-instant (the one that failed)
    current_model = "llama-3.1-8B-instant"
    fallback_chain = [current_model]
    
    print(f"Starting model: {current_model}")
    
    # Follow fallback chain
    while True:
        fallback = choose_fallback(current_model)
        if not fallback:
            break
        fallback_chain.append(fallback)
        print(f"  └─ Fallback: {fallback}")
        current_model = fallback
        
        # Prevent infinite loops
        if len(fallback_chain) > 10:
            print("  ⚠️  Breaking to prevent infinite loop")
            break
    
    print(f"\n✅ Complete fallback chain: {' → '.join(fallback_chain)}")
    
    # Test all models have fallbacks
    print(f"\n🔍 Checking all models have fallbacks:")
    from config.config_loader import list_models
    
    models = list_models()
    for model in models:
        model_id = model['id']
        fallback = choose_fallback(model_id)
        if fallback:
            print(f"✅ {model_id} → {fallback}")
        else:
            print(f"❌ {model_id} → NO FALLBACK")
    
    print("\n🎯 Test completed!")

if __name__ == "__main__":
    test_fallback_chain()
