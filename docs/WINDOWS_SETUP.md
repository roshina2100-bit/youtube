# Windows Setup Guide

This guide covers Windows-specific installation and configuration details for the Cinematic Multi-Language Video Studio.

## Windows-Specific Prerequisites

### 1. Enable Long Paths (Required)
Windows has a 260-character path limit by default. Projects with deep folder structures will fail without this.

**Option A: Group Policy (Windows Pro/Enterprise)**
1. Run `gpedit.msc`
2. Navigate to: Computer Configuration → Administrative Templates → System → Filesystem
3. Enable "Enable Win32 long paths"

**Option B: Registry (All Editions)**
```powershell
# Run as Administrator
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```
Restart required after either method.

### 2. PowerShell Execution Policy
```powershell
# Run as Administrator
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 3. Windows Terminal (Recommended)
```powershell
winget install Microsoft.WindowsTerminal
```

### 4. Developer Mode
Settings → Privacy & Security → For Developers → Developer Mode: On

## Backend Windows Configuration

### 1. Virtual Environment in PowerShell
```powershell
cd backend
python -m venv .venv

# If activation fails:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
.\.venv\Scripts\Activate.ps1
```

### 2. FFmpeg on Windows
**Install via winget:**
```powershell
winget install Gyan.FFmpeg
```

**Verify installation:**
```powershell
ffmpeg -version
ffprobe -version
```

**If not in PATH after install:**
1. Find install location: `where ffmpeg`
2. Add to System PATH: `C:\Program Files\Gyan\FFmpeg\bin`
3. Restart terminal

### 3. CUDA Setup (For GPU Acceleration)

**Check NVIDIA Driver:**
```powershell
nvidia-smi
```

**Install CUDA Toolkit 12.x:**
1. Download from: https://developer.nvidia.com/cuda-toolkit
2. Run installer (Express installation)
3. Verify: `nvcc --version`

**Install cuDNN:**
1. Download from: https://developer.nvidia.com/cudnn
2. Extract and copy to CUDA directory
3. Or use conda: `conda install -c conda-forge cudnn`

**PyTorch with CUDA:**
```powershell
# In activated venv
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### 4. Python Packages with Native Dependencies

Some packages require Visual C++ Build Tools:
```powershell
# Install Build Tools
winget install Microsoft.VisualStudio.2022.BuildTools

# Or install via Visual Studio Installer:
# Workloads → Desktop development with C++
# Individual components → MSVC v143, Windows 10/11 SDK
```

**Common problematic packages:**
- `tokenizers` (Rust-based) - usually has wheels
- `bitsandbytes` - Windows support limited, use CPU fallback
- `flash-attn` - Not available on Windows, disable in config

### 5. Hugging Face CLI
```powershell
pip install huggingface_hub[cli]
huggingface-cli login  # Optional, for gated models
```

## Frontend Windows Configuration

### 1. Node.js Version Manager (Optional)
```powershell
# Install nvm-windows
winget install CoreyButler.NVMforWindows

# Restart terminal, then:
nvm install lts
nvm use lts
```

### 2. Angular CLI
```powershell
npm install -g @angular/cli
```

### 3. File Watcher Limits
If you get `ENOSPC` errors:
```powershell
# Not typically needed on Windows, but if using WSL:
# echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf
```

## Project Root on Windows

### Recommended Locations
```
F:\CinematicVideoStudio\projects\     # Dedicated drive (best)
D:\Projects\CinematicVideoStudio\     # Secondary drive
C:\Users\<username>\CinematicVideoStudio\projects\  # User folder
```

### Avoid
- `C:\Program Files\` (requires admin)
- OneDrive/Dropbox synced folders (sync conflicts)
- Paths with special characters or spaces

### Set in .env
```env
PROJECT_ROOT=F:\CinematicVideoStudio\projects
```

### Set in UI
Settings → General → Project Root Directory → Browse

## Path Handling in Code

### Always Use pathlib
```python
from pathlib import Path

# Good
project_root = Path("F:/CinematicVideoStudio/projects")
project_path = project_root / "MyProject" / "source" / "video.mp4"

# Bad - hardcoded separators
project_path = "F:\\CinematicVideoStudio\\projects\\MyProject\\source\\video.mp4"

# Bad - string concatenation
project_path = project_root + "\\MyProject\\source\\video.mp4"
```

### Windows Paths in YAML Config
```yaml
# Use forward slashes (YAML/JSON standard)
model_path: "C:/Models/llama-3-8b-instruct"

# Or raw strings with double backslashes
model_path: "C:\\Models\\llama-3-8b-instruct"
```

### Subprocess on Windows
```python
import subprocess
from pathlib import Path

# Good - argument array, no shell
ffmpeg_path = Path("ffmpeg")  # Assumes in PATH
cmd = [
    str(ffmpeg_path),
    "-i", str(input_path),
    "-c:v", "libx264",
    str(output_path)
]
result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

# Bad - shell=True with user input
# subprocess.run(f"ffmpeg -i {input_path} ...", shell=True)  # SECURITY RISK
```

## Windows-Specific Issues & Fixes

### 1. "Access Denied" on File Operations
- Run terminal as Administrator (for system folders)
- Check folder permissions: Right-click → Properties → Security
- Disable Controlled Folder Access for project folder

### 2. "File in Use" Errors
- Ensure no other process has file open (VS Code, Explorer preview)
- Use `handle.exe` from Sysinternals to find locking process
- Implement retry logic with backoff in code

### 3. Symlink/Junction Issues
- Requires Developer Mode or Admin
- Use `Path.is_symlink()` to detect
- Prefer `shutil.copy2()` over symlinks for portability

### 4. Case Sensitivity
- Windows is case-insensitive, Linux is case-sensitive
- Always use consistent casing in code
- Test on both if cross-platform

### 5. Line Endings
```gitattributes
# In .gitattributes
* text=auto
*.py text eol=lf
*.ts text eol=lf
*.json text eol=lf
*.yaml text eol=lf
*.md text eol=lf
```

### 6. Console Encoding
```powershell
# In PowerShell profile or before running
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

```python
# In Python scripts
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
```

## Running as a Service (Production)

### Using NSSM (Non-Sucking Service Manager)
```powershell
# Install NSSM
winget install nssm

# Create service for backend
nssm install CinematicVideoStudioBackend
# Path: C:\path\to\.venv\Scripts\python.exe
# Startup directory: C:\path\to\backend
# Arguments: -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Create service for frontend (if serving static files)
nssm install CinematicVideoStudioFrontend
# Path: C:\path\to\node.exe
# Arguments: C:\path\to\frontend\server.js
```

### Using Windows Task Scheduler
For simpler setups, use Task Scheduler with "At startup" trigger.

## Development Workflow on Windows

### 1. Multi-Terminal Setup (Windows Terminal)
Create a profile that opens multiple tabs:
```json
{
  "name": "CinematicVideoStudio Dev",
  "tabs": [
    { "title": "Backend", "commandline": "powershell -NoExit -Command \"cd backend; .venv\\Scripts\\Activate.ps1; python -m uvicorn app.main:app --reload\"" },
    { "title": "Frontend", "commandline": "powershell -NoExit -Command \"cd frontend; npm start\"" },
    { "title": "Tests", "commandline": "powershell -NoExit -Command \"cd backend; .venv\\Scripts\\Activate.ps1\"" }
  ]
}
```

### 2. VS Code Tasks (`.vscode/tasks.json`)
```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Start Backend",
      "type": "shell",
      "command": "powershell",
      "args": ["-NoExit", "-Command", "cd backend; .venv\\Scripts\\Activate.ps1; python -m uvicorn app.main:app --reload"],
      "group": "build",
      "presentation": { "panel": "new" }
    },
    {
      "label": "Start Frontend",
      "type": "shell",
      "command": "powershell",
      "args": ["-NoExit", "-Command", "cd frontend; npm start"],
      "group": "build",
      "presentation": { "panel": "new" }
    },
    {
      "label": "Run Backend Tests",
      "type": "shell",
      "command": "powershell",
      "args": ["-Command", "cd backend; .venv\\Scripts\\Activate.ps1; python -m pytest -v"],
      "group": "test"
    }
  ]
}
```

### 3. VS Code Launch Config (`.vscode/launch.json`)
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"],
      "cwd": "${workspaceFolder}/backend",
      "envFile": "${workspaceFolder}/backend/.env"
    },
    {
      "name": "Attach to Frontend",
      "type": "chrome",
      "request": "attach",
      "port": 9222,
      "webRoot": "${workspaceFolder}/frontend/src"
    }
  ]
}
```

## Antivirus/Defender Exclusions

Add these folders to Windows Defender exclusions for performance:
- Project root (e.g., `F:\CinematicVideoStudio\projects`)
- Backend virtual environment (`.venv`)
- Frontend `node_modules`
- Model cache directories

## Backup Strategy

### Project Backup
```powershell
# Simple backup script
$projectRoot = "F:\CinematicVideoStudio\projects"
$backupRoot = "F:\Backups\CinematicVideoStudio"
$date = Get-Date -Format "yyyyMMdd_HHmmss"

Compress-Archive -Path "$projectRoot\*" -DestinationPath "$backupRoot\projects_$date.zip"
```

### Automated Backup (Task Scheduler)
Run daily/weekly with the above script.

## Troubleshooting Windows Issues

| Issue | Solution |
|-------|----------|
| `python` not found | Reinstall Python with "Add to PATH" checked |
| `npm` not found | Reinstall Node.js, restart terminal |
| `ffmpeg` not found | Add FFmpeg bin to System PATH |
| CUDA out of memory | Reduce batch size, enable CPU offload, close other apps |
| Port 8000/4200 in use | `netstat -ano | findstr :8000` then `taskkill /PID <pid> /F` |
| Module import errors | Ensure venv activated, reinstall requirements |
| Permission denied | Run as Admin, check folder permissions |
| Long path errors | Enable long paths (see above) |

## Next Steps

1. Complete [Installation](INSTALLATION.md) for full setup
2. Configure [Models](MODEL_SETUP.md) for local AI
3. Review [Architecture](ARCHITECTURE.md) for system understanding