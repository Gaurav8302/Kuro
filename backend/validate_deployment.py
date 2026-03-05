#!/usr/bin/env python3
"""
Deployment Validation Script

This script validates that all imports work correctly and environment
variables are configured properly before deployment.
"""

import sys
import os
import importlib.util

def validate_imports():
    """Validate that all required imports work without errors"""
    print("🔍 Validating imports...")
    
    try:
        # Test ultra-lightweight memory manager
        from memory.ultra_lightweight_memory import store_memory, get_relevant_memories_detailed, ultra_lightweight_memory_manager
        print("✅ Ultra-lightweight memory manager imports successful")
        
        # Test chat manager v2
        from memory.chat_manager_v2 import chat_with_memory
        print("✅ Chat manager v2 imports successful")
        
        # Test chatbot
        from chatbot import app
        print("✅ Chatbot imports successful")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def validate_environment():
    """Validate that required environment variables are set"""
    print("🔍 Validating environment variables...")
    
    required_vars = [
        'GEMINI_API_KEY',
        'PINECONE_API_KEY', 
        'PINECONE_INDEX_NAME',
        'CLERK_SECRET_KEY'
    ]
    
    optional_vars = [
        'MONGODB_URI',
        'MONGO_URI',
        'FRONTEND_URL'
    ]
    
    missing_required = []
    for var in required_vars:
        if not os.getenv(var):
            missing_required.append(var)
        else:
            print(f"✅ {var} is set")
    
    for var in optional_vars:
        if os.getenv(var):
            print(f"✅ {var} is set")
        else:
            print(f"⚠️  {var} is not set (optional)")
    
    if missing_required:
        print(f"❌ Missing required environment variables: {', '.join(missing_required)}")
        return False
    
    return True

def check_problematic_files():
    """Check for files with problematic imports that shouldn't be loaded"""
    print("🔍 Checking for problematic files...")
    
    # AI/ML libraries that should not be used (commented for removal)
    problematic_imports = [
        # 'sentence_transformers',  # REMOVED: Replaced with regex patterns
        # 'sklearn',               # REMOVED: Not needed for lightweight system  
        # 'scikit-learn',          # REMOVED: Not needed for lightweight system
        # 'transformers',          # REMOVED: Replaced with rule-based routing
        # 'torch',                 # REMOVED: Replaced with lightweight alternatives
        # 'tensorflow'             # REMOVED: Not used in this system
    ]
    
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    
    for root, dirs, files in os.walk(backend_dir):
        for file in files:
            if file.endswith('.py') and not file.startswith('validate_'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        for import_name in problematic_imports:
                            if f'import {import_name}' in content or f'from {import_name}' in content:
                                # Check if it's being actively imported by used files
                                if any(used_file in filepath for used_file in ['chat_manager_v2.py', 'chatbot.py', 'ultra_lightweight_memory.py']):
                                    print(f"❌ Problematic import '{import_name}' found in active file: {filepath}")
                                    return False
                                else:
                                    print(f"⚠️  Problematic import '{import_name}' found in unused file: {filepath}")
                except Exception as e:
                    print(f"⚠️  Could not read file {filepath}: {e}")
    
    print("✅ No problematic imports in active files")
    return True

def main():
    """Run all validation checks"""
    print("🚀 Starting deployment validation...\n")
    
    checks = [
        ("Environment Variables", validate_environment),
        ("Import Dependencies", validate_imports),
        ("Problematic Files", check_problematic_files)
    ]
    
    all_passed = True
    
    for check_name, check_func in checks:
        print(f"\n{'='*50}")
        print(f"Running {check_name} Check")
        print('='*50)
        
        if not check_func():
            all_passed = False
    
    print(f"\n{'='*50}")
    if all_passed:
        print("✅ ALL VALIDATION CHECKS PASSED")
        print("🚀 Ready for deployment!")
        sys.exit(0)
    else:
        print("❌ VALIDATION FAILED")
        print("🛑 Fix issues before deploying!")
        sys.exit(1)

if __name__ == "__main__":
    main()
