# Kuro AI — Development Conventions

## Naming

| Category | Convention | Example |
|----------|-----------|---------|
| Python variables | `snake_case` | `user_message` |
| Python functions | `snake_case` | `generate_response()` |
| Python classes | `PascalCase` | `ModelRouter` |
| TypeScript variables | `camelCase` | `userMessage` |
| TypeScript functions | `camelCase` | `generateResponse()` |
| React components | `PascalCase` | `ChatMessage` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_TOKENS` |
| Files | `kebab-case` | `model-router.ts` |

## TypeScript

- Strict mode enabled (`strict: true` in tsconfig)
- No `any` type — use `unknown` with type guards
- Explicit types preferred over inference for function signatures
- Interface for props, type for unions/utility types

## Python

- PEP 8 compliance with Black formatting
- Type hints for all function parameters and returns
- Google-style docstrings for all classes and functions
- Async/await for all I/O operations
- Logging instead of print statements

## Components

- Single responsibility per component
- Reusable and composable
- Functional components with hooks (no class components)
- Error boundaries for component error handling
- Accessibility (ARIA labels, keyboard navigation)

## Testing

**Required:**
- Unit tests for all utility functions
- Integration tests for API endpoints
- Safety tests for prompt/response validation
- Component tests with React Testing Library

**How to run:**
```bash
# Backend
cd backend && python -m pytest

# Frontend
cd frontend && npm test
```

## Documentation

Update docs whenever:
- Architecture changes (update `architecture.md`)
- Decisions change (update `decisions.md`)
- Roadmap changes (update `roadmap.md`)
- New knowledge gained (update `memory.md`)
- New features added (update `onboarding.md` features list)

## Commits

Format: `type(scope): message`

**Types:** feat, fix, docs, style, refactor, test, chore

```bash
# Good
git commit -m "feat(auth): add voice input support"
git commit -m "fix(memory): resolve leak in chat manager"
git commit -m "docs(api): update endpoint documentation"

# Bad
git commit -m "fixed stuff"
git commit -m "update"
```

## Pull Requests

Must include:
- Purpose (what and why)
- Changes (key files modified)
- Testing (how verified)
- Risks (potential regressions)
