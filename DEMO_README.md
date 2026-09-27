# Cinematic Multi-Language Video Studio - Demo

This demo script demonstrates the complete YouTube URL to final multilingual video pipeline.

## Running the Demo

```bash
cd backend
python ../demo_pipeline.py
```

## What the Demo Does

1. **Initializes all services** - ProjectManager, ProviderRegistry, WorkflowEngine, YouTubeSourceHandler, PipelineCompletionService
2. **Creates a demo project** with target languages (English, Spanish, French)
3. **Shows project directory structure** - All required folders are created automatically
4. **Tests YouTube URL validation** - Validates various YouTube URL formats
4. **Tests YouTube import (mocked)** - Simulates downloading video and transcript
5. **Shows pipeline stages** - Displays all 20 pipeline stages with dependencies
6. **Tests pipeline completion service** - Shows how the pipeline orchestrates the workflow

## Requirements

- Python 3.12+
- Backend dependencies installed (`pip install -r requirements.txt`)
- Test mode enabled (uses mock providers)

## Running the Demo

```bash
cd backend
python ../demo_pipeline.py
```

## Expected Output

The demo will show:
1. Service initialization
2. Project creation with full directory structure
3. YouTube URL validation for various formats
4. Mock YouTube import (creates dummy video and transcript files)
5. Pipeline stages with dependencies
5. Pipeline completion service status

## Next Steps After Demo

1. Configure real AI models in Settings > Models
2. Add YouTube API key for real transcript downloading
3. Configure FFmpeg path if not in system PATH
4. Run backend: `python -m uvicorn app.main:app --reload`
5. Run frontend: `npm start` (in frontend/)
5. Open http://localhost:4200 in browser