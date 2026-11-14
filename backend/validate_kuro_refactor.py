#!/usr/bin/env python3
"""Validate Kuro AI refactor - check model mappings and skills"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from config.config_loader import get_model, list_models
from skills.skill_manager import skill_manager

def validate_models():
    print("🔧 Validating Kuro AI Model Configuration")
    print("=" * 60)
    
    models = list_models()
    groq_models = []
    openrouter_models = []
    
    print(f"📊 Total models in registry: {len(models)}")
    
    for model in models:
        model_id = model['id']
        if '/' in model_id and ':free' in model_id:
            openrouter_models.append(model_id)
        else:
            groq_models.append(model_id)
        
        capabilities = model.get('capabilities', [])
        fallback = model.get('fallback', [])
        print(f"✅ {model_id}")
        print(f"   Capabilities: {capabilities}")
        print(f"   Fallbacks: {fallback[:2]}{'...' if len(fallback) > 2 else ''}")
    
    print(f"\n🚀 Groq models: {len(groq_models)}")
    for m in groq_models:
        print(f"   - {m}")
    
    print(f"\n🌐 OpenRouter models: {len(openrouter_models)}")  
    for m in openrouter_models:
        print(f"   - {m}")

def validate_skills():
    print(f"\n🎯 Validating Skills Configuration")
    print("=" * 60)
    
    # Force reload to get current skills
    skill_manager._load_skills(force=True)
    skills = skill_manager._skills
    
    print(f"📊 Total skills loaded: {len(skills)}")
    
    # Group by priority
    by_priority = {}
    for skill in skills:
        prio = skill.priority
        if prio not in by_priority:
            by_priority[prio] = []
        by_priority[prio].append(skill)
    
    for priority in sorted(by_priority.keys(), reverse=True):
        skill_group = by_priority[priority]
        print(f"\n🔥 Priority {priority} ({len(skill_group)} skills):")
        for skill in skill_group:
            triggers = skill.trigger_patterns[:3] 
            trigger_preview = f"{triggers}{'...' if len(skill.trigger_patterns) > 3 else ''}"
            print(f"   ✅ {skill.name}: {trigger_preview}")

if __name__ == "__main__":
    validate_models()
    validate_skills()
    print(f"\n✨ Kuro AI refactor validation completed!")
