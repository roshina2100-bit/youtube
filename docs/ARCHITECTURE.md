# Architecture

## System Overview

The Cinematic Multi-Language Video Studio follows a clean architecture with clear separation between frontend, backend, and AI providers.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (Angular)                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │  Dashboard  │ │  Projects   │ │   Models    │ │  Settings   │            │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘            │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    Project Workspace                                 │    │
│  │  SOURCE → TRANSCRIPT → STORY → CHARACTERS → SCENES → LANGUAGES      │    │
│  │  → PROMPTS → IMAGES → VIDEO → AUDIO → RENDER → OUTPUT               │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │ HTTP/REST + WebSocket
┌──────────────────────────────────▼──────────────────────────────────────────┐
│                              BACKEND (FastAPI)                               │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
│  │   Project    │ │   Workflow   │ │  Provider    │ │   Asset      │       │
│  │   Manager    │ │   Engine     │ │  Registry    │ │   Manager    │       │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘       │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                        Service Layer                                  │  │
│  │  Transcript • Story • Character • Scene • Translation • Prompt       │  │
│  │  ImageGen • VideoGen • TTS • Music • SFX • Render                    │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        ▼                          ▼                          ▼
┌───────────────┐          ┌───────────────┐          ┌───────────────┐
│ Local Python  │          │ NotebookLM/   │          │    FFmpeg     │
│ Models        │          │ API Adapter   │          │  (Rendering)  │
│               │          │  (Optional)   │          │               │
│ • Transformers│          │               │          │ • Concat      │
│ • Diffusers   │          │ • Config via  │          │ • Mix         │
│ • Whisper     │          │   .env        │          │ • Scale       │
│ • TTS         │          │ • Capability  │          │ • Subtitles   │
│ • MusicGen    │          │   Matrix      │          │ • Encode      │
└───────────────┘          └───────────────┘          └───────────────┘
```

## Core Components

### 1. Project Manager (`backend/app/services/project_manager.py`)
- Creates, loads, validates project folders
- Manages `project.json` manifest
- Handles project discovery and resume

### 2. Workflow Engine (`backend/app/workflow/engine.py`)
- Async job orchestration using asyncio
- Persistent job state in `project/jobs/`
- States: QUEUED → RUNNING → PAUSED → COMPLETED/FAILED/CANCELLED
- Cancellation, retry, progress tracking

### 3. Provider Registry (`backend/app/providers/registry.py`)
- Manages all AI provider implementations
- Capability matrix validation
- Model lifecycle (load/unload/idle)

### 4. Provider Interfaces (`backend/app/providers/interfaces.py`)
Abstract base classes for:
- `LLMProvider` - Text generation, analysis
- `TranslationProvider` - Context-aware translation
- `TranscriptionProvider` - Speech-to-text
- `LanguageDetectionProvider` - Language identification
- `EmbeddingProvider` - Vector embeddings
- `ImageGenerationProvider` - Text-to-image
- `VideoGenerationProvider` - Image-to-video, text-to-video
- `TTSProvider` - Text-to-speech
- `MusicGenerationProvider` - Music generation
- `SoundEffectProvider` - SFX generation

### 5. Local Providers (`backend/app/providers/local/`)
Concrete implementations using Python libraries:
- `TransformersLLMProvider` - Hugging Face transformers
- `FasterWhisperTranscriptionProvider` - faster-whisper
- `DiffusersImageProvider` - Stable Diffusion via diffusers
- `DiffusersVideoProvider` - Video models via diffusers
- `TransformersTTSProvider` - TTS via transformers
- `MusicGenProvider` - MusicGen via transformers

### 6. Mock Providers (`backend/app/providers/mock/`)
Deterministic implementations for testing:
- No external dependencies
- No GPU required
- Fast execution
- Predictable outputs

### 7. NotebookLM Adapter (`backend/app/providers/external/notebooklm.py`)
- Configuration via `.env`
- Capability detection
- Connection testing
- Graceful degradation

## Data Flow

### Project Creation
```
User → Frontend → POST /api/v1/projects → ProjectManager.create()
→ Creates folder structure → Writes project.json → Returns project_id
```

### Story Analysis Pipeline
```
Transcript → StoryService.analyze() → LLMProvider.generate()
→ StoryGraph (acts, events, characters, themes) → Saved to story/
```

### Character Pipeline
```
StoryGraph.characters → CharacterService.extract() → CharacterBible
→ For each character: PromptEngine.generate_character_prompt()
→ ImageGenerationProvider.generate() → Character images (versioned)
→ User approval → Lock character_version
```

### Translation Pipeline
```
Scene + Context → TranslationProvider.translate()
→ SemanticReview.validate() → Flag drift → Save to languages/{lang}/
```

### Rendering Pipeline
```
SilentMasterVideo + LanguageAudio → FFmpeg.mux()
→ output/{language}/final.mp4
```

## File-Based Persistence

All data stored as files in project folder:

| Data Type | Format | Location |
|-----------|--------|----------|
| Project manifest | JSON | `project.json` |
| Transcript | TXT, JSON, JSONL | `transcript/` |
| Story graph | JSON | `story/` |
| Characters | JSON | `characters/` |
| Scenes | JSON | `scenes/` |
| Translations | JSON | `languages/{lang}/` |
| Prompts | TXT (versioned) | `prompts/` |
| Images | PNG/JPG (versioned) | `images/` |
| Video | MP4 (versioned) | `video/` |
| Audio | WAV/MP3 (versioned) | `audio/` |
| Approvals | JSON | `approvals/` |
| Logs | JSONL | `logs/` |

## Versioning Strategy

Every generated asset uses semantic versioning:
```
prompt_v001.txt → prompt_v002.txt → prompt_v003.txt
character_v001.png → character_v002.png
scene_v001.mp4 → scene_v002.mp4
```

`project.json` tracks active versions:
```json
{
  "active_versions": {
    "character_001": "v003",
    "scene_0001": "v002"
  }
}
```

## Security Architecture

- **No secrets in project files** - Only in `.env`
- **Path validation** - All paths resolved relative to project root
- **Subprocess safety** - Argument arrays only, no shell=True
- **Input validation** - Pydantic models on all endpoints
- **CORS** - Restricted to configured origins
- **Rate limiting** - Per-endpoint limits

## Performance Considerations

- **Model lifecycle management** - Load on demand, unload when idle
- **Concurrency limits** - Max 1 GPU job by default
- **CPU fallback** - Enabled where technically possible
- **Streaming responses** - For long-running operations
- **Progress tracking** - Real-time updates via WebSocket

## Extensibility Points

1. **New Providers** - Implement provider interfaces
2. **New Languages** - Add to language configuration
3. **New Export Formats** - Add export handlers
4. **Custom Prompt Templates** - Extend PromptEngine
5. **New Video Effects** - Extend FFmpeg renderer