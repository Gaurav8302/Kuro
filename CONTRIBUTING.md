# Contributing to Kuro AI

Thank you for your interest in contributing to Kuro AI! This document provides guidelines and information for contributors.

## 🤝 How to Contribute

### Reporting Issues

1. **Search existing issues** first to avoid duplicates
2. **Use issue templates** when available
3. **Provide detailed information**:
   - Clear description of the problem
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Python version, Node.js version)
   - Screenshots or logs if applicable

### Suggesting Features

1. **Open a feature request** issue
2. **Describe the feature** in detail
3. **Explain the use case** and benefits
4. **Consider implementation** complexity
5. **Be open to discussion** and feedback

### Pull Requests

1. **Fork the repository**
2. **Create a feature branch** from `main`
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make your changes** following our coding standards
4. **Test thoroughly** (see Testing section)
5. **Update documentation** as needed
6. **Commit with clear messages**
   ```bash
   git commit -m "feat: add amazing feature that does X"
   ```
7. **Push to your fork**
   ```bash
   git push origin feature/amazing-feature
   ```
8. **Create a pull request** with detailed description

## 🏗️ Development Setup

### Prerequisites

- **Python 3.11+** with pip
- **Node.js 18+** with npm
- **Git** for version control
- **MongoDB** (local or cloud)
- **API Keys**: Gemini, Clerk, Pinecone

### Local Development

1. **Clone your fork**
   ```bash
   git clone https://github.com/yourusername/Kuro.git
   cd Kuro
   ```

2. **Backend setup**
   ```bash
   cd backend
   pip install -r requirements.txt
   cp .env.example .env
   # Edit .env with your API keys
   python chatbot.py
   ```

3. **Frontend setup**
   ```bash
   cd frontend
   npm install
   cp .env.example .env.local
   # Edit .env.local with your API keys
   npm run dev
   ```

4. **Run tests**
   ```bash
   # Backend tests
   cd backend
   python -m pytest
   python test_kuro_system.py

   # Frontend tests
   cd frontend
   npm test
   ```

## 📝 Coding Standards

### Python (Backend)

- **PEP 8** compliance with Black formatting
- **Type hints** for all function parameters and returns
- **Docstrings** for all classes and functions (Google style)
- **Error handling** with appropriate exceptions
- **Logging** instead of print statements
- **Async/await** for I/O operations

```python
async def generate_response(message: str, context: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate AI response using Kuro prompt system.
    
    Args:
        message (str): User's input message
        context (Optional[str]): Additional context from memory
        
    Returns:
        Dict[str, Any]: Response data with text and metadata
        
    Raises:
        APIError: If AI service is unavailable
    """
    try:
        # Implementation here
        pass
    except Exception as e:
        logger.error(f"Failed to generate response: {e}")
        raise
```

### TypeScript (Frontend)

- **Strict TypeScript** configuration
- **ESLint + Prettier** for formatting
- **Functional components** with hooks
- **Type definitions** for all props and state
- **Error boundaries** for component error handling
- **Accessibility** (ARIA labels, keyboard navigation)

```typescript
interface ChatMessageProps {
  message: string;
  sender: 'user' | 'ai';
  timestamp: Date;
  onRetry?: () => void;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ 
  message, 
  sender, 
  timestamp, 
  onRetry 
}) => {
  // Component implementation
};
```

### Git Commit Messages

Follow [Conventional Commits](https://conventionalcommits.org/):

- `feat:` new features
- `fix:` bug fixes
- `docs:` documentation changes
- `style:` formatting changes
- `refactor:` code refactoring
- `test:` adding or updating tests
- `chore:` maintenance tasks

Examples:
```
feat: add voice input support for chat
fix: resolve memory leak in chat manager
docs: update API documentation for new endpoints
refactor: optimize prompt building performance
```

## 🧪 Testing

### Backend Testing

- **Unit tests** for all utility functions
- **Integration tests** for API endpoints
- **Safety tests** for prompt and response validation
- **Performance tests** for memory management

```python
# Example test
import pytest
from utils.kuro_prompt import build_kuro_prompt

def test_build_kuro_prompt():
    """Test prompt building with various inputs."""
    result = build_kuro_prompt("Hello", context="Previous conversation")
    
    assert "system_instruction" in result
    assert "user_prompt" in result
    assert "Kuro" in result["system_instruction"]
    assert "Hello" in result["user_prompt"]
```

### Frontend Testing

- **Component tests** with React Testing Library
- **Hook tests** for custom React hooks
- **Integration tests** for API calls
- **E2E tests** for critical user flows

```typescript
// Example test
import { render, screen } from '@testing-library/react';
import ChatMessage from './ChatMessage';

test('renders chat message correctly', () => {
  render(
    <ChatMessage 
      message="Hello world" 
      sender="user" 
      timestamp={new Date()} 
    />
  );
  
  expect(screen.getByText('Hello world')).toBeInTheDocument();
});
```

## 📁 Project Structure

When adding new features, follow the existing structure:

```
backend/
├── utils/              # Core utilities (prompt, safety, etc.)
├── memory/             # Memory management system
├── routes/             # API endpoints
├── database/           # Database operations
├── tests/              # Test files
└── chatbot.py          # Main application

frontend/
├── src/
│   ├── components/     # Reusable UI components
│   ├── pages/          # Page components
│   ├── hooks/          # Custom React hooks
│   ├── lib/            # Utility functions
│   ├── types/          # TypeScript definitions
│   └── tests/          # Test files
└── package.json
```

## 🔒 Security Guidelines

- **Never commit** API keys or sensitive data
- **Use environment variables** for configuration
- **Validate all inputs** on both frontend and backend
- **Sanitize outputs** to prevent XSS
- **Follow OWASP** security guidelines
- **Report security issues** privately via email

## 📚 Documentation

- **Update README.md** for new features
- **Add JSDoc/docstrings** for new functions
- **Update API documentation** for new endpoints
- **Include examples** in documentation
- **Update CHANGELOG.md** for releases

## 🚀 Release Process

1. **Feature development** on feature branches
2. **Testing** and code review
3. **Merge to main** with squash commits
4. **Update version** in package.json/setup.py
5. **Update CHANGELOG.md**
6. **Create release tag**
7. **Deploy to staging** for final testing
8. **Deploy to production**

## 🏷️ Labels and Milestones

### Issue Labels

- `bug` - Something isn't working
- `enhancement` - New feature or request
- `documentation` - Improvements or additions to docs
- `good first issue` - Good for newcomers
- `help wanted` - Extra attention is needed
- `priority: high` - High priority issue
- `priority: low` - Low priority issue

### Milestones

- `v1.1.0` - Next minor release
- `v2.0.0` - Next major release
- `bug fixes` - Ongoing bug fixes

## 🎯 Code Review Guidelines

### For Reviewers

- **Be constructive** and helpful
- **Focus on code quality** and maintainability
- **Check for security** issues
- **Verify tests** are included
- **Ensure documentation** is updated
- **Test locally** when possible

### For Contributors

- **Respond promptly** to feedback
- **Ask questions** if unclear
- **Make requested changes** or explain why not
- **Keep PRs focused** on single features
- **Rebase and squash** commits when requested

## 💬 Community

- **Be respectful** and inclusive
- **Help other contributors**
- **Share knowledge** and best practices
- **Report violations** of code of conduct
- **Follow project guidelines**

## 📞 Getting Help

- **GitHub Issues** - For bugs and feature requests
- **Discussions** - For questions and general discussion
- **Email** - For security issues or private matters
- **Discord** - For real-time community chat (coming soon)

---

Thank you for contributing to Kuro AI! Your efforts help make this project better for everyone. 🎉
