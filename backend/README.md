# Cinematic Multi-Language Video Studio - Backend

FastAPI backend for the Cinematic Multi-Language Video Studio.

## Prerequisites

- Python 3.12+
- FFmpeg (in PATH)
- Virtual environment (recommended)

## Installation

```bash
cd backend
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# Windows CMD
.\.venv\Scripts\activate.bat
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
```

## Development

```bash
# Start development server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
python -m pytest

# Run tests with coverage
python -m pytest --cov=app --cov-report=html

# Run specific test file
python -m pytest tests/test_project_manager.py -v

# Type checking
python -m mypy app

# Linting
python -m ruff check app
python -m ruff format app
```

## Project Structure

```
backend/
├── app/
│   ├── api/              # REST API endpoints
│   │   ├── health.py     # Health checks
│   │   ├── projects.py   # Project management
│   │   ├── models.py     # Model management
│   │   ├── providers.py  # Provider management
│   │   └── jobs.py       # Job management
│   ├── core/             # Core configuration and utilities
│   │   ├── config.py     # Settings management
│   │   ├── logging.py    # Structured logging
│   │   └── security.py   # Security utilities
│   ├── models/           # Pydantic models
│   │   ├── project.py    # Project models
│   │   ├── transcript.py # Transcript models
│   │   ├── story.py      # Story models
│   │   ├── character.py  # Character models
│   │   ├── scene.py      # Scene models
│   │   ├── translation.py # Translation models
│   │   ├── job.py        # Job models
│   │   ├── provider.py   # Provider models
│   │   └── asset.py      # Asset models
│   ├── providers/        # AI provider implementations
│   │   ├── interfaces.py # Abstract interfaces
│   │   ├── registry.py   # Provider registry
│   │   ├── local/        # Local Python providers
│   │   ├── mock/         # Mock providers for testing
│   │   └── external/     # External API providers
│   ├── services/         # Business logic services
│   │   ├── project_manager.py
│   │   ├── story_service.py
│   │   ├── character_service.py
│   │   ├── scene_service.py
│   │   ├── translation_service.py
│   │   └── prompt_engine.py
│   ├── workflow/         # Workflow engine
│   │   └── engine.py     # Job orchestration
│   ├── utils/            # Utility functions
│   │   └── ffmpeg.py     # FFmpeg wrapper
│   └── main.py           # FastAPI application entry point
├── config/               # Configuration files
│   └── models.yaml       # Model configurations
├── tests/                # Test files
│   ├── conftest.py       # Pytest fixtures
│   └── test_project_manager.py
├── requirements.txt      # Python dependencies
├── pyproject.toml        # Project configuration
└── main.py               # Entry point
```

## Configuration

### Environment Variables (.env)

Copy `.env.example` to `.env` and configure:

```env
# Project storage
PROJECT_ROOT=F:/CinematicVideoStudio/projects

# FFmpeg
FFMPEG_PATH=ffmpeg
FFPROBE_PATH=ffprobe

# NotebookLM (optional)
NOTEBOOKLM_ENABLED=false
NOTEBOOKLM_API_KEY=
NOTEBOOKLM_ENDPOINT=
NOTEBOOKLM_PROJECT_ID=
NOTEBOOKLM_MODEL=

# Provider defaults
AI_DEFAULT_PROVIDER=local_python
AI_ALLOW_EXTERNAL_PROVIDER=true
AI_FALLBACK_TO_LOCAL=false

# Performance
MAX_CONCURRENT_GPU_JOBS=1
ENABLE_CPU_FALLBACK=true
MODEL_IDLE_TIMEOUT=300

# Security
SECRET_KEY=your-secret-key
CORS_ORIGINS=http://localhost:4200,http://127.0.0.1:4200
MAX_UPLOAD_SIZE=524288000
```

### Model Configuration (config/models.yaml)

Configure model paths and parameters in `config/models.yaml`. See the file for all available options.

## API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Key API Endpoints

### Projects
- `POST /api/v1/projects` - Create project
- `GET /api/v1/projects` - List projects
- `GET /api/v1/projects/{id}` - Get project
- `PATCH /api/v1/projects/{id}` - Update project
- `DELETE /api/v1/projects/{id}` - Delete project

### Jobs
- `POST /api/v1/projects/{id}/jobs` - Create job
- `GET /api/v1/projects/{id}/jobs` - List jobs
- `GET /api/v1/projects/{id}/jobs/{job_id}` - Get job status
- `POST /api/v1/projects/{id}/jobs/{job_id}/cancel` - Cancel job
- `POST /api/v1/projects/{id}/jobs/{job_id}/retry` - Retry job

### Models
- `GET /api/v1/models` - List models
- `GET /api/v1/models/{type}/{provider}/{model}` - Get model info
- `POST /api/v1/models/test` - Test model
- `POST /api/v1/models/{type}/{provider}/{model}/load` - Load model
- `POST /api/v1/models/{type}/{provider}/{model}/unload` - Unload model

### Providers
- `GET /api/v1/providers` - List providers
- `GET /api/v1/providers/capabilities` - Get capability matrix

## Testing

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=app --cov-report=html

# Run specific test
python -m pytest tests/test_project_manager.py -v

# Run integration tests
python -m pytest tests/integration -v

# Run E2E tests (requires mock providers)
TEST_MODE=true python -m pytest tests/e2e -v
```

## AI Providers

### Local Python Providers
- **LLM**: Transformers (Llama, Mistral, Qwen, etc.)
- **Transcription**: Faster-Whisper
- **Translation**: Transformers (NLLB, M2M100)
- **Language Detection**: FastText
- **Embeddings**: Sentence Transformers
- **Image Generation**: Diffusers (SDXL)
- **Video Generation**: Diffusers (SVD)
- **TTS**: Transformers (XTTS v2)
- **Music**: Transformers (MusicGen)
- **SFX**: Diffusers (AudioLDM 2)

### Mock Providers
Used for testing without models/GPU. Enable with `TEST_MODE=true`.

### External Providers
- NotebookLM (placeholder for future API)

## Workflow Engine

The workflow engine orchestrates jobs using asyncio:
- Persistent job state in `project/jobs/`
- Job states: QUEUED → RUNNING → COMPLETED/FAILED/CANCELLED
- Concurrency control with semaphores
- Automatic retry with exponential backoff
- Job recovery after restart

## File-Based Persistence

All data stored as files in project directory:
- `project.json` - Project manifest
- `transcript/` - Transcript files
- `story/` - Story graph
- `characters/` - Character bibles
- `scenes/` - Scene definitions
- `languages/` - Per-language workspaces
- `prompts/` - Generated prompts
- `images/` - Generated images
- `video/` - Video assets
- `audio/` - Audio assets
- `output/` - Final rendered videos
- `approvals/` - Approval records
- `logs/` - Project logs
- `jobs/` - Job state

## Security

- Path traversal protection
- Safe subprocess execution (argument arrays only)
- Input validation with Pydantic
- CORS configuration
- No secrets in project files
- Structured logging without sensitive data

## Performance

- Model lifecycle management (load/unload/idle)
- GPU memory monitoring
- CPU fallback support
- Concurrent job limits
- Streaming responses for long operations

## Logging

Structured JSON logging:
- Application logs: `application/logs/`
- Project logs: `project/logs/`
- Error logs: `application/logs/errors.jsonl`

## Deployment

### Windows Service (NSSM)
```powershell
nssm install CinematicVideoStudioBackend
# Path: C:\path\to\.venv\Scripts\python.exe
# Arguments: -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Docker (Optional)
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Troubleshooting

### Common Issues

1. **ModuleNotFoundError**: Ensure virtual environment is activated
2. **CUDA not found**: Install CUDA toolkit or use CPU mode
3. **FFmpeg not found**: Add FFmpeg to PATH or set FFMPEG_PATH
4. **Port in use**: Change port or kill existing process
5. **Permission denied**: Run as administrator or check folder permissions

### Logs

Check `application/logs/application.jsonl` for detailed logs.

## Contributing

1. Follow PEP 8 style guide
2. Use type hints
3. Write tests for new features
4. Update documentation
5. Follow conventional commits