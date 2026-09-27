# Installation Guide

## Prerequisites

### System Requirements
- **OS**: Windows 10/11 (64-bit), Linux (Ubuntu 22.04+), macOS 13+
- **RAM**: 16 GB minimum, 32 GB recommended
- **Storage**: 50 GB free space (more for models and projects)
- **GPU**: NVIDIA GPU with 8+ GB VRAM (optional but recommended)

### Required Software

#### 1. Python 3.12+
```powershell
# Windows - using winget
winget install Python.Python.3.12

# Or download from python.org
# Verify: python --version
```

#### 2. Node.js 20+ (LTS)
```powershell
# Windows - using winget
winget install OpenJS.NodeJS.LTS

# Or download from nodejs.org
# Verify: node --version && npm --version
```

#### 3. FFmpeg
```powershell
# Windows - using winget
winget install Gyan.FFmpeg

# Or download from ffmpeg.org
# Add to PATH
# Verify: ffmpeg -version
```

#### 4. Git
```powershell
# Windows - using winget
winget install Git.Git

# Verify: git --version
```

#### 5. Visual Studio Code (Recommended)
```powershell
winget install Microsoft.VisualStudioCode
```

## Backend Setup

### 1. Navigate to Backend Directory
```powershell
cd backend
```

### 2. Create Virtual Environment
```powershell
python -m venv .venv
```

### 3. Activate Virtual Environment
```powershell
# PowerShell
.\.venv\Scripts\Activate.ps1

# Command Prompt
.\.venv\Scripts\activate.bat

# Git Bash
source .venv/Scripts/activate
```

### 4. Upgrade Pip and Install Dependencies
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Install Development Dependencies (Optional)
```powershell
pip install -r requirements-dev.txt
```

### 6. Configure Environment
```powershell
copy ..\.env.example .env
# Edit .env with your settings
```

### 7. Run Tests
```powershell
python -m pytest
```

### 8. Start Development Server
```powershell
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at: http://localhost:8000
API docs at: http://localhost:8000/docs

## Frontend Setup

### 1. Navigate to Frontend Directory
```powershell
cd frontend
```

### 2. Install Dependencies
```powershell
npm install
```

### 3. Run Tests
```powershell
npm test
```

### 4. Start Development Server
```powershell
npm start
```

Frontend will be available at: http://localhost:4200

### 5. Build for Production
```powershell
npm run build
```

Output in `dist/cinematic-video-studio/`

## Model Setup (Local Provider)

### 1. Create Models Directory
```powershell
mkdir C:\Models
```

### 2. Download Models Manually

**LLM (e.g., Llama 3 8B Instruct)**
```powershell
# Using huggingface-cli (install: pip install huggingface_hub)
huggingface-cli download meta-llama/Meta-Llama-3-8B-Instruct --local-dir C:\Models\llama-3-8b-instruct
```

**Transcription (Whisper Large v3)**
```powershell
huggingface-cli download Systran/faster-whisper-large-v3 --local-dir C:\Models\whisper-large-v3
```

**Image Generation (SDXL)**
```powershell
huggingface-cli download stabilityai/stable-diffusion-xl-base-1.0 --local-dir C:\Models\sdxl-base
huggingface-cli download stabilityai/stable-diffusion-xl-refiner-1.0 --local-dir C:\Models\sdxl-refiner
```

**Video Generation (SVD)**
```powershell
huggingface-cli download stabilityai/stable-video-diffusion-img2vid-xt --local-dir C:\Models\svd-xt
```

**TTS (XTTS v2)**
```powershell
huggingface-cli download coqui/XTTS-v2 --local-dir C:\Models\xtts-v2
```

**Music Generation (MusicGen)**
```powershell
huggingface-cli download facebook/musicgen-large --local-dir C:\Models\musicgen-large
```

### 3. Configure Model Paths

Edit `backend/config/models.yaml`:
```yaml
models:
  llm:
    provider: local_python
    backend: transformers
    model_path: "C:/Models/llama-3-8b-instruct"
    device: "cuda"
    torch_dtype: "float16"
  
  transcription:
    provider: local_python
    backend: faster_whisper
    model_path: "C:/Models/whisper-large-v3"
    device: "cuda"
    compute_type: "float16"
  
  image:
    provider: local_python
    backend: diffusers
    model_path: "C:/Models/sdxl-base"
    refiner_path: "C:/Models/sdxl-refiner"
    device: "cuda"
    torch_dtype: "float16"
  
  video:
    provider: local_python
    backend: diffusers
    model_path: "C:/Models/svd-xt"
    device: "cuda"
    torch_dtype: "float16"
  
  tts:
    provider: local_python
    backend: transformers
    model_path: "C:/Models/xtts-v2"
    device: "cuda"
  
  music:
    provider: local_python
    backend: transformers
    model_path: "C:/Models/musicgen-large"
    device: "cuda"
```

### 4. Verify Model Loading
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -c "
from app.providers.local.llm import TransformersLLMProvider
provider = TransformersLLMProvider()
provider.load()
print('LLM loaded successfully')
provider.unload()
"
```

## NotebookLM/API Setup (Optional)

### 1. Enable in .env
```env
NOTEBOOKLM_ENABLED=true
NOTEBOOKLM_API_KEY=your_api_key
NOTEBOOKLM_ENDPOINT=https://api.notebooklm.example.com
NOTEBOOKLM_PROJECT_ID=your_project_id
NOTEBOOKLM_MODEL=gemini-pro
```

### 2. Test Connection
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -c "
from app.providers.external.notebooklm import NotebookLMProvider
provider = NotebookLMProvider()
result = provider.test_connection()
print(f'Connection: {result}')
"
```

## Project Root Configuration

### 1. Set Default Project Root
Edit `.env`:
```env
PROJECT_ROOT=F:\CinematicVideoStudio\projects
```

### 2. Or Configure in UI
Settings → General → Project Root Directory

## Verification

### 1. Health Check
```powershell
# Backend
curl http://localhost:8000/health

# Frontend
# Open http://localhost:4200 in browser
```

### 2. Run Full Test Suite
```powershell
# Backend
cd backend
.\.venv\Scripts\Activate.ps1
python -m pytest -v

# Frontend
cd frontend
npm test
```

### 3. Run E2E Test (Mock Providers)
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
TEST_MODE=true python -m pytest tests/e2e/test_full_pipeline.py -v
```

## Troubleshooting

### Python Issues
- **ModuleNotFoundError**: Ensure virtual environment is activated
- **CUDA not found**: Install CUDA toolkit, or set `device: "cpu"` in models.yaml
- **Out of memory**: Reduce batch size, enable CPU offload, use smaller models

### Node Issues
- **ENOSPC**: Increase file watchers: `echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf`
- **Port in use**: Change port in `angular.json` or kill process on 4200

### FFmpeg Issues
- **Not found**: Add FFmpeg to PATH, or set FFMPEG_PATH in .env
- **Codec errors**: Ensure full FFmpeg build (not static)

### Model Loading Issues
- **Path errors**: Use forward slashes in YAML (C:/Models/...)
- **Permission denied**: Run as administrator or check folder permissions
- **Version conflicts**: Check transformers, torch, diffusers compatibility

## Next Steps

1. Read [Windows Setup](WINDOWS_SETUP.md) for Windows-specific details
2. Read [Model Setup](MODEL_SETUP.md) for detailed model configuration
3. Read [Architecture](ARCHITECTURE.md) to understand the system
4. Create your first project in the UI