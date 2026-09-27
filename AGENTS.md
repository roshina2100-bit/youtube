# AGENTS.md

## Project: Cinematic Multi-Language Video Studio

### Agent Instructions

This document provides guidance for AI agents working on this codebase.

---

## Architecture Overview

**Frontend**: Angular 18+ with TypeScript, Angular Material, RxJS, Angular Signals
**Backend**: Python 3.12+ with FastAPI, Pydantic v2, asyncio
**Persistence**: File-based (JSON, JSONL, TXT, Markdown, YAML, images, audio, video)
**AI Providers**: Local Python models + Optional NotebookLM/API adapter

---

## Key Principles

1. **Local-First**: Everything runs on the user's Windows machine
2. **File-Based Persistence**: No databases, no Redis, no external dependencies
3. **Provider Abstraction**: Clean interfaces for all AI capabilities
4. **Project Self-Containment**: Each project folder is completely portable
5. **Human Approval Required**: AI never auto-finalizes critical assets
6. **Version Everything**: Never silently overwrite generated assets
7. **Windows-First**: Use pathlib, Windows-compatible subprocess handling

---

## Development Workflow

### Phase-Based Development
- Execute one phase at a time
- After each phase: inspect, implement, test, lint, type-check, document
- Never skip verification
- Update this file if agent patterns change

### Code Standards
- **Python**: Type hints required, Pydantic v2 models, async/await
- **TypeScript**: Strict mode, Angular Signals, RxJS observables
- **File Paths**: Always use `pathlib.Path`
- **Subprocess**: Use argument arrays, never shell=True with user input
- **Secrets**: Never log API keys, store in `.env` only

---

## Project Structure

```
CinematicVideoStudio/
├── backend/                 # FastAPI application
│   ├── app/
│   │   ├── api/            # REST endpoints
│   │   ├── core/           # Configuration, security
│   │   ├── models/         # Pydantic models
│   │   ├── services/       # Business logic
│   │   ├── providers/      # AI provider implementations
│   │   ├── workflow/       # Job engine, orchestration
│   │   └── utils/          # Helpers
│   ├── tests/
│   ├── requirements.txt
│   └── pyproject.toml
├── frontend/                # Angular application
│   ├── src/
│   │   ├── app/
│   │   │   ├── core/       # Services, guards, interceptors
│   │   │   ├── features/   # Feature modules
│   │   │   ├── shared/     # Shared components, pipes, directives
│   │   │   └── layout/     # Layout components
│   │   ├── assets/
│   │   └── environments/
│   ├── package.json
│   └── angular.json
├── docs/                    # Documentation
├── tests/                   # Integration/E2E tests
├── .env.example
├── .gitignore
├── README.md
└── AGENTS.md
```

---

## Agent-Specific Guidelines

### When Adding New Features
1. Check existing provider interfaces first
2. Add provider implementation (local + mock)
3. Add API endpoints
4. Add frontend components
5. Add tests
6. Update documentation

### When Modifying Providers
- Never break the provider interface contract
- Always implement both local and mock versions
- Update capability matrix
- Test with both providers

### When Working with File System
- Use `pathlib.Path` exclusively
- Validate paths are within project root
- Use atomic writes (write to temp, then rename)
- Version important files

### When Handling AI Operations
- Check provider capabilities before execution
- Show clear errors with actionable suggestions
- Never fake successful AI operations
- Log detailed errors, show user-friendly messages

---

## Testing Requirements

- Unit tests for all services and providers
- Integration tests for API → File System → Workflow
- E2E test with mock providers (complete pipeline)
- Test mode must work without internet, GPU, or external APIs

---

## Documentation Standards

Every phase must update:
- README.md (if user-facing changes)
- ARCHITECTURE.md (if structural changes)
- API documentation (OpenAPI/Swagger)
- Phase completion report