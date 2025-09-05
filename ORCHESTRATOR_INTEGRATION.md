# Orchestrator Integration Summary

## Overview

A new **orchestrator layer** has been successfully integrated into the Kuro chatbot backend. This layer acts as a preprocessing filter between user queries and the main Kuro LLM, enhancing query understanding and optimizing response generation.

## Architecture

```
User Query → Orchestrator → Enhanced Query → Kuro LLM → Response
```

## Files Modified/Created

### New Files
- **`backend/orchestrator.py`** - Main orchestrator implementation
- **`backend/test_orchestrator_integration.py`** - Integration test suite

### Modified Files
- **`backend/memory/chat_manager.py`** - Integrated orchestrator into chat processing pipeline
- **`ENVIRONMENT_SETUP.md`** - Added OPENROUTER_API_KEY requirement

## Key Features

### 1. OpenRouter Model Integration
- Uses 4 models in round-robin fashion:
  - `deepseek/deepseek-v3.1`
  - `openai/gpt-oss-120b` 
  - `z-ai/glm-4.5-air`
  - `moonshotai/kimi-k2`

### 2. Task Classification
Automatically classifies queries into:
- **math** - Mathematical problems and equations
- **code** - Programming and coding tasks
- **rag** - Information retrieval queries  
- **chat** - General conversation
- **other** - Uncategorized queries

### 3. Query Enhancement
- Expands user queries into optimized prompts
- Suggests appropriate tools (sympy, pinecone, etc.)
- Provides step-by-step instructions
- Specifies expected response formats

### 4. Intelligent Routing
- **Math tasks**: Placeholder for math solver integration
- **RAG tasks**: Enhanced search queries for better retrieval
- **Code tasks**: Expanded prompts with examples and specifications
- **Chat tasks**: Context-aware conversation handling

## Integration Points

### ChatManager Integration
The orchestrator is integrated into `ChatManager.chat_with_memory()`:

1. **Pre-processing**: User query → Orchestrator analysis
2. **Query Enhancement**: Original message → Enhanced prompt
3. **Context Addition**: Orchestrator insights added to response context
4. **RAG Optimization**: Enhanced queries for better document retrieval

### Safety & Fallbacks
- **Graceful degradation**: Falls back to original query if orchestrator fails
- **Confidence thresholds**: Only uses enhanced queries above confidence threshold (0.1)
- **Safe JSON parsing**: Robust parsing with fallback structure
- **Error handling**: Comprehensive error handling with logging

## Environment Setup

### Required Environment Variables
The orchestrator uses the same environment variable names as the existing codebase:
```bash
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

### Render Deployment
Since you mentioned the environment variables are already set in Render, the orchestrator should work automatically once deployed. The system uses:
- `OPENROUTER_API_KEY` (consistent with existing `utils/openrouter_client.py`)
- Same variable names as documented in `DEPLOYMENT_ENVIRONMENT_VARS.md`

### Local Testing
For local development, ensure your `.env` file includes:
```bash
OPENROUTER_API_KEY=your_openrouter_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here  # Required for ChatManager
PINECONE_API_KEY=your_pinecone_api_key_here  # Required for memory system
```

### Configuration
- **Temperature**: 0.3 (for consistent JSON output)
- **Max tokens**: 1000 (sufficient for orchestration)
- **Timeout**: 30 seconds
- **Confidence threshold**: 0.1 for basic usage, 0.3 for RAG

## Usage Examples

### Mathematical Query
```python
# Input: "solve x^2 + 5x + 6 = 0"
# Orchestrator output:
{
    "task": "math",
    "input": "x^2 + 5x + 6 = 0", 
    "expanded_prompt": "You are a math tutor. Solve this quadratic equation step by step...",
    "instructions": ["identify equation type", "apply quadratic formula", "show work"],
    "tools": ["sympy"],
    "confidence": 0.95
}
```

### Code Generation
```python
# Input: "write a Python function to reverse a string"
# Orchestrator output:
{
    "task": "code",
    "input": "write a Python function to reverse a string",
    "expanded_prompt": "Create a Python function with clear documentation...",
    "instructions": ["define function", "implement reversal logic", "add examples"],
    "tools": ["python"],
    "confidence": 0.90
}
```

## Performance Impact

- **Latency**: Adds ~1-2 seconds for OpenRouter API call
- **Accuracy**: Improves response relevance through better prompting
- **Resource usage**: Minimal additional memory overhead
- **Reliability**: Fallback mechanisms ensure system stability

## Future Enhancements

1. **Math Solver Integration**: Connect with SymPy or similar libraries
2. **Code Execution**: Sandbox for running and testing generated code
3. **Advanced RAG**: Multi-step reasoning with retrieved documents
4. **Learning**: Adaptive model selection based on performance
5. **Caching**: Cache orchestration results for repeated queries

## Testing

Run the integration test:
```bash
cd backend
python test_orchestrator_integration.py
```

## Logging

The orchestrator provides comprehensive logging:
- Model selection and API calls
- JSON parsing success/failures
- Task classification results
- Integration with ChatManager
- Error handling and fallbacks

## Deployment Notes

1. Ensure `OPENROUTER_API_KEY` is set in production environment
2. Monitor API usage and costs
3. Adjust confidence thresholds based on performance
4. Consider rate limiting for OpenRouter API calls

The orchestrator integration enhances Kuro's ability to understand user intent and provide more targeted, accurate responses while maintaining system reliability and performance.
