# Cinematic Multi-Language Video Studio

A Windows-first, local-first cinematic video production system that transforms authorized source video/transcripts into fully produced multilingual videos.

## Overview

This application takes a source video or transcript, analyzes the story, identifies characters and scenes, generates character references and cinematic prompts, translates/adapts the story into multiple languages, generates visuals, generates language-specific audio, and produces a separate video for every selected language.

**All processing happens locally on your Windows machine.** No cloud services, databases, or external AI APIs are required (optional NotebookLM/API integration available).

## Features

- **Project-Based Workflow**: Each project is a self-contained folder on disk
- **Multi-Language Support**: 12+ target languages (English, Telugu, Hindi, Kannada, Tamil, Malayalam, Bengali, French, German, Portuguese, Dutch, Spanish)
- **Provider Choice**: Select Local Python Models or NotebookLM/API per AI operation
- **Character Consistency**: Canonical character references locked across all scenes
- **Cinematic Prompt Engineering**: Detailed prompts for image/video generation
- **Context-Aware Translation**: Preserves meaning, emotion, cultural context
- **Silent Master Video**: Reusable visual track across all languages
- **Language-Specific Audio**: Independent TTS, music, SFX per language
- **FFmpeg Rendering**: Professional video/audio composition
- **Human Approval Gates**: Manual approval for characters, translations, final output
- **Version Control**: All generated assets versioned (v001, v002, etc.)
- **Resume Capability**: Reopen projects after restart, continue incomplete jobs

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Angular Frontend                          │
│  Dashboard • Projects • Models • Settings                    │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP/WebSocket
┌──────────────────────────▼──────────────────────────────────┐
│                    FastAPI Backend                           │
│  Project Manager • Workflow Engine • Provider Registry       │
└──────────────────────────┬──────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│ Local Python  │  │ NotebookLM/   │  │ FFmpeg        │
│ Models        │  │ API Adapter   │  │ Rendering     │
│ (Transformers,│  │ (Optional)    │  │ (Local)       │
│  Diffusers,   │  │               │  │               │
│  Whisper, etc)│  │               │  │               │
└───────────────┘  └───────────────┘  └───────────────┘
```

## Project Structure

Each project lives in its own folder:

```
projects/
└── MyProject/
    ├── project.json              # Project manifest
    ├── source/                   # Source media & metadata
    ├── transcript/               # Original, normalized, segmented
    ├── story/                    # Story graph, acts, events, themes
    ├── characters/               # Character bible, images, approvals
    ├── locations/                # Location references
    ├── scenes/                   # Cinematic scene breakdown
    ├── languages/                # Per-language workspaces
    ├── prompts/                  # All generated prompts (versioned)
    ├── images/                   # Generated images (versioned)
    ├── video/                    # Silent master, previews
    ├── audio/                    # Per-language narration, dialogue, music, SFX
    ├── output/                   # Final videos per language
    ├── approvals/                # Approval records
    ├── logs/                     # Project-specific logs
    └── exports/                  # Export packages
```

## Requirements

### System
- Windows 10/11 (primary), Linux/macOS (experimental)
- Python 3.12+
- Node.js 20+
- FFmpeg (in PATH)
- Git

### Python Packages (Backend)
- fastapi, uvicorn
- pydantic, pydantic-settings
- python-dotenv
- pyyaml
- transformers, torch, diffusers (for local models)
- faster-whisper (for transcription)
- And more (see `backend/requirements.txt`)

### Node Packages (Frontend)
- @angular/core, @angular/material, @angular/cdk
- rxjs
- And more (see `frontend/package.json`)

### Optional: GPU Acceleration
- NVIDIA GPU with CUDA 12+
- 8GB+ VRAM recommended for local models

## Quick Start

### Option A: Docker (Recommended - Easiest Setup)

The easiest way to run the application is using Docker Compose, which handles all dependencies automatically.

```powershell
git clone <repository>
cd CinematicVideoStudio

# Copy environment template
copy .env.example .env
# Edit .env with your settings (optional NotebookLM API keys)

# Build and start all services
.\docker-start.ps1 build
.\docker-start.ps1 up

# Or use the batch file on Windows
docker-start.bat build
docker-start.bat up
```

**Access the application:**
- **Frontend**: http://localhost
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

**Useful Docker commands:**
```powershell
# View logs
.\docker-start.ps1 logs
.\docker-start.ps1 logs backend

# Check status
.\docker-start.ps1 status

# Stop services
.\docker-start.ps1 down

# Restart services
.\docker-start.ps1 restart

# Clean up (removes all containers, networks, volumes)
.\docker-start.ps1 clean
```

### Option B: Manual Setup (Development)

### 1. Clone and Configure

```powershell
git clone <repository>
cd CinematicVideoStudio

# Copy environment template
copy .env.example .env
# Edit .env with your settings (optional NotebookLM API keys)
```

### 2. Backend Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pytest                    # Run tests
python -m uvicorn app.main:app --reload  # Start server
```

### 3. Frontend Setup

```powershell
cd frontend
npm install
npm test                            # Run tests
npm run build                       # Production build
npm start                           # Dev server (http://localhost:4200)
```

### 4. Configure Models (Local Provider)

Edit `backend/config/models.yaml` or use the Models page in the UI to set model paths:

```yaml
models:
  llm:
    provider: local_python
    backend: transformers
    model_path: "C:\Models\llama-3-8b-instruct"
  
  transcription:
    provider: local_python
    backend: faster_whisper
    model_path: "C:\Models\whisper-large-v3"
  
  # ... etc
```

### Environment Variables (`.env`)
```env
# NotebookLM/API (optional)
NOTEBOOKLM_ENABLED=false
NOTEBOOKLM_API_KEY=
NOTEBOOKLM_ENDPOINT=
NOTEBOOKLM_PROJECT_ID=
NOTEBOOKLM_MODEL=
NOTEBOOKLM_TIMEOUT_SECONDS=300
NOTEBOOKLM_MAX_RETRIES=3

# Provider defaults
AI_DEFAULT_PROVIDER=local_python
AI_ALLOW_EXTERNAL_PROVIDER=true
AI_FALLBACK_TO_LOCAL=false
```

## Docker Configuration

### Docker Compose Services

The application runs as two Docker containers orchestrated by Docker Compose:

| Service | Port | Description |
|---------|------|-------------|
| **frontend** | 80 | Angular frontend served via Nginx |
| **backend** | 8000 | FastAPI backend API |

### Docker Commands

```powershell
# Build images
.\docker-start.ps1 build

# Start services
.\docker-start.ps1 up

# View logs
.\docker-start.ps1 logs
.\docker-start.ps1 logs backend

# Check status
.\docker-start.ps1 status

# Stop services
.\docker-start.ps1 down

# Restart services
.\docker-start.ps1 restart

# Clean up (removes containers, networks, volumes)
.\docker-start.ps1 clean
```

### Docker Volumes

The following directories are persisted as Docker volumes:

| Host Path | Container Path | Description |
|-----------|----------------|-------------|
| `./backend/projects` | `/app/projects` | Project files and generated assets |
| `./backend/logs` | `/app/logs` | Application logs |
| `./backend/temp` | `/app/temp` | Temporary files |
| `./backend/config` | `/app/config` | Configuration files (read-only) |

### GPU Support (Optional)

For GPU acceleration with local models, ensure you have:
- NVIDIA GPU with CUDA 12+
- Docker with NVIDIA Container Toolkit installed
- Add to `docker-compose.yml` under backend service:

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

### Building Custom Images

```powershell
# Build with no cache
.\docker-start.ps1 build

# Or manually
docker-compose build --no-cache --parallel
```

### Troubleshooting Docker

| Issue | Solution |
|-------|----------|
| Port 80/8000 already in use | Stop conflicting services or change ports in `docker-compose.yml` |
| Out of memory | Increase Docker memory limit in Docker Desktop settings |
| FFmpeg not found | Ensure FFmpeg is installed in the backend container (included in Dockerfile) |
| Permission denied | Run PowerShell as Administrator or fix Docker Desktop permissions |
| Models not loading | Check `LOCAL_MODELS_DIR` in `.env` and ensure models are downloaded |

### Viewing Logs

```powershell
# All services
.\docker-start.ps1 logs

# Backend only
.\docker-start.ps1 logs backend

# Frontend only
.\docker-start.ps1 logs frontend
```

### Accessing the Application

| Service | URL |
|---------|-----|
| Frontend UI | http://localhost |
| Backend API | http://localhost:8000 |
| API Documentation (Swagger) | http://localhost:8000/docs |
| API Documentation (ReDoc) | http://localhost:8000/redoc |

## Configuration

### Application Settings (`config/application.json`)
- Project root directory
- Default providers
- Performance limits
- Logging levels

### Model Configuration (`config/models.yaml`)
- Model paths, backends, capabilities
- Resource requirements

### Environment Variables (`.env`)
```env
# NotebookLM/API (optional)
NOTEBOOKLM_ENABLED=false
NOTEBOOKLM_API_KEY=
NOTEBOOKLM_ENDPOINT=
NOTEBOOKLM_PROJECT_ID=
NOTEBOOKLM_MODEL=
NOTEBOOKLM_TIMEOUT_SECONDS=300
NOTEBOOKLM_MAX_RETRIES=3

# Provider defaults
AI_DEFAULT_PROVIDER=local_python
AI_ALLOW_EXTERNAL_PROVIDER=true
AI_FALLBACK_TO_LOCAL=false
```

## Testing

```powershell
# Backend tests
cd backend
.\.venv\Scripts\Activate.ps1
python -m pytest                    # Unit tests
python -m pytest tests/integration  # Integration tests

# Frontend tests
cd frontend
npm test                            # Unit tests
npm run e2e                         # E2E tests (requires running backend)

# Full E2E with mock providers (no internet, no GPU, no models)
python -m pytest tests/e2e/test_full_pipeline.py -v
```

## Demo: YouTube URL to Final Video Pipeline

Run the interactive demo to see the complete pipeline in action:

```powershell
cd backend
python ../demo_pipeline.py
```

This demo will:
1. Initialize all services (ProjectManager, ProviderRegistry, WorkflowEngine, YouTubeSourceHandler, PipelineCompletionService)
2. Create a demo project with target languages (English, Spanish, French)
3. Show the complete project directory structure
4. Test YouTube URL validation for various formats
5. Simulate YouTube import (mocked - creates dummy video and transcript)
5. Display all 20 pipeline stages with their dependencies
6. Test the pipeline completion service

See [DEMO_README.md](DEMO_README.md) for more details.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Installation](docs/INSTALLATION.md)
- [Windows Setup](docs/WINDOWS_SETUP.md)
- [Model Setup](docs/MODEL_SETUP.md)
- [NotebookLM Setup](docs/NOTEBOOKLM_SETUP.md)
- [AI Providers](docs/AI_PROVIDERS.md)
- [Project Format](docs/PROJECT_FORMAT.md)
- [Prompt Engine](docs/PROMPT_ENGINE.md)
- [Media Pipeline](docs/MEDIA_PIPELINE.md)
- [Testing](docs/TESTING.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Security](docs/SECURITY.md)
- [Performance](docs/PERFORMANCE.md)

## Security

- No API keys stored in project files
- Secrets only in `.env` (gitignored)
- Safe subprocess execution (argument arrays only)
- Path traversal protection
- Input validation on all endpoints
- CORS configured for local development only

## License

MIT License - See LICENSE file for details.

## Contributing

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for development guidelines.

## Support

- Check [Troubleshooting](docs/TROUBLESHOOTING.md)
- Review logs in `project/logs/` and `application/logs/`
- Enable debug logging in Settings