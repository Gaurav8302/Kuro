#!/usr/bin/env python3
"""
Kuro AI Prompt System Demo

This script demonstrates the new production-ready prompt system
showing how Kuro's identity, safety, and quality systems work together.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def demo_kuro_identity():
    """Demonstrate Kuro's identity awareness"""
    print("🤖 KURO IDENTITY DEMO")
    print("=" * 50)
    
    from utils.kuro_prompt import build_kuro_prompt
    
    # Test identity question
    prompt_package = build_kuro_prompt("Who are you?")
    
    print("📝 System Instruction (excerpt):")
    system_lines = prompt_package["system_instruction"].split('\n')[:5]
    for line in system_lines:
        print(f"   {line}")
    print("   ...")
    
    print(f"\n📨 User Prompt:")
    print(prompt_package["user_prompt"])
    
    print("\n✅ When asked 'Who are you?', Kuro will respond:")
    print("   'I am Kuro, your friendly AI assistant here to help with anything you need.'")

def demo_safety_system():
    """Demonstrate safety validation"""
    print("\n\n🛡️ SAFETY SYSTEM DEMO")
    print("=" * 50)
    
    from utils.safety import validate_response
    
    test_responses = [
        ("Safe technical response", "Python is a programming language. Here's how to get started: ```python\nprint('Hello, World!')\n```"),
        ("Potential hallucination", "According to recent studies in 2024, Python became 500% faster."),
        ("Unhelpful response", "I can't help with that question."),
        ("High quality response", "Here's how to learn Python:\n\n1. **Start with basics** - variables and functions\n2. **Practice daily** - solve coding problems\n3. **Build projects** - apply what you learn")
    ]
    
    for label, response in test_responses:
        is_valid, assessment = validate_response(response)
        safety_level = assessment.get('safety_level', 'unknown')
        quality_score = assessment.get('quality_score', 0)
        
        status = "✅ SAFE" if is_valid else "⚠️ UNSAFE"
        print(f"\n{status} {label}:")
        print(f"   Safety: {safety_level.value if hasattr(safety_level, 'value') else safety_level}")
        print(f"   Quality: {quality_score:.2f}/1.0")
        if assessment.get('warnings'):
            print(f"   Warnings: {len(assessment['warnings'])}")

def demo_prompt_structure():
    """Demonstrate prompt structure"""
    print("\n\n📋 PROMPT STRUCTURE DEMO")
    print("=" * 50)
    
    from utils.kuro_prompt import build_kuro_prompt
    
    user_message = "How do I build a web app with Python?"
    context = "User is interested in backend development and has basic Python knowledge."
    
    prompt_package = build_kuro_prompt(user_message, context)
    
    print("🎯 Input:")
    print(f"   Message: {user_message}")
    print(f"   Context: {context}")
    
    print(f"\n📊 Generated Prompt Package:")
    print(f"   System Instruction: {len(prompt_package['system_instruction'])} characters")
    print(f"   User Prompt: {len(prompt_package['user_prompt'])} characters")
    
    print(f"\n📝 User Prompt Structure:")
    lines = prompt_package['user_prompt'].split('\n')
    for i, line in enumerate(lines[:10]):  # First 10 lines
        print(f"   {i+1:2d}: {line}")
    if len(lines) > 10:
        print(f"   ... ({len(lines)-10} more lines)")

def demo_configuration():
    """Demonstrate configuration options"""
    print("\n\n⚙️ CONFIGURATION DEMO")
    print("=" * 50)
    
    from utils.kuro_prompt import KuroPromptBuilder, KuroPromptConfig
    
    configs = [
        ("Default (Friendly)", KuroPromptConfig()),
        ("Professional", KuroPromptConfig(personality_level="professional", max_response_words=200)),
        ("Casual", KuroPromptConfig(personality_level="casual", max_response_words=150, enable_markdown=False))
    ]
    
    for name, config in configs:
        builder = KuroPromptBuilder(config)
        system_instruction = builder.build_system_instruction()
        
        print(f"\n🎨 {name} Configuration:")
        print(f"   Personality: {config.personality_level}")
        print(f"   Max words: {config.max_response_words}")
        print(f"   Markdown: {config.enable_markdown}")
        print(f"   System instruction: {len(system_instruction)} chars")

if __name__ == "__main__":
    print("🚀 KURO AI PROMPT SYSTEM DEMONSTRATION")
    print("=" * 60)
    print("This demo shows the production-ready prompt engineering system")
    print("that makes Kuro a consistent, safe, and helpful AI assistant.\n")
    
    try:
        demo_kuro_identity()
        demo_safety_system()
        demo_prompt_structure()
        demo_configuration()
        
        print("\n\n🎉 DEMO COMPLETE!")
        print("=" * 60)
        print("The Kuro AI prompt system is ready for production use!")
        print("Key benefits:")
        print("✅ Consistent Kuro personality")
        print("✅ Advanced safety guardrails")
        print("✅ Quality response validation")
        print("✅ Configurable behavior")
        print("✅ Enterprise-grade reliability")
        
    except Exception as e:
        print(f"\n❌ Demo error: {e}")
        print("Make sure all dependencies are installed and the system is properly set up.")
