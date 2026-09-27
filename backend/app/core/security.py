"""
Security utilities for the Cinematic Video Studio backend.
Path validation, input sanitization, safe subprocess execution.
"""

import re
import secrets
import hashlib
from pathlib import Path
from typing import Optional, List
from fastapi import HTTPException, status
from pydantic import BaseModel, field_validator


class SecurityError(HTTPException):
    """Security-related HTTP exception."""
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def validate_project_path(project_root: Path, project_id: str, 
                          requested_path: str) -> Path:
    """
    Validate that a requested path is within the project directory.
    Prevents path traversal attacks.
    """
    # Resolve project root
    project_root = project_root.resolve()
    project_dir = (project_root / project_id).resolve()
    
    # Ensure project directory exists and is within project root
    try:
        project_dir.relative_to(project_root)
    except ValueError:
        raise SecurityError(f"Invalid project ID: {project_id}")
    
    # Resolve requested path
    requested = (project_dir / requested_path).resolve()
    
    # Ensure requested path is within project directory
    try:
        requested.relative_to(project_dir)
    except ValueError:
        raise SecurityError(f"Path traversal attempt detected: {requested_path}")
    
    return requested


def validate_file_extension(filename: str, allowed_extensions: List[str]) -> bool:
    """Validate file extension against allowed list."""
    ext = Path(filename).suffix.lower()
    return ext in [e.lower() for e in allowed_extensions]


def validate_mime_type(mime_type: str, allowed_types: List[str]) -> bool:
    """Validate MIME type against allowed list."""
    return mime_type in allowed_types


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """Sanitize filename for safe filesystem usage."""
    # Remove path components
    filename = Path(filename).name
    
    # Remove dangerous characters
    filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', filename)
    
    # Limit length
    if len(filename) > max_length:
        name, ext = Path(filename).stem, Path(filename).suffix
        max_name_len = max_length - len(ext)
        filename = name[:max_name_len] + ext
    
    # Ensure not empty
    if not filename or filename in ('.', '..'):
        filename = f"file_{secrets.token_hex(8)}"
    
    return filename


def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token."""
    return secrets.token_urlsafe(length)


def compute_sha256(file_path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def compute_sha256_bytes(data: bytes) -> str:
    """Compute SHA-256 hash of bytes."""
    return hashlib.sha256(data).hexdigest()


class SafeSubprocess:
    """Safe subprocess execution with argument validation."""
    
    # Allowed commands (executable names)
    ALLOWED_COMMANDS = {
        "ffmpeg", "ffprobe", "ffplay",
        "python", "python3",
    }
    
    # Dangerous patterns that should never appear in arguments
    DANGEROUS_PATTERNS = [
        r";", r"&&", r"\|\|", r"`", r"\$\(.*\)",  # Shell metacharacters
        r">", r"<", r">>",  # Redirection
        r"\$\{.*\}",  # Variable expansion
    ]
    
    @classmethod
    def validate_command(cls, command: List[str]) -> None:
        """Validate command and arguments for safety."""
        if not command:
            raise SecurityError("Empty command")
        
        # Check executable
        executable = Path(command[0]).name.lower()
        if executable not in cls.ALLOWED_COMMANDS:
            raise SecurityError(f"Command not allowed: {executable}")
        
        # Check arguments for dangerous patterns
        for arg in command[1:]:
            for pattern in cls.DANGEROUS_PATTERNS:
                if re.search(pattern, arg):
                    raise SecurityError(f"Dangerous pattern in argument: {arg}")
    
    @classmethod
    async def run(cls, command: List[str], timeout: int = 300, 
                  cwd: Optional[Path] = None, **kwargs) -> "subprocess.CompletedProcess":
        """Run command safely with validation."""
        import subprocess
        
        cls.validate_command(command)
        
        # Ensure no shell=True
        kwargs.pop("shell", None)
        
        # Run with timeout
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
                **kwargs
            )
            return result
        except subprocess.TimeoutExpired as e:
            raise SecurityError(f"Command timed out after {timeout}s") from e
        except FileNotFoundError as e:
            raise SecurityError(f"Command not found: {command[0]}") from e
        except Exception as e:
            raise SecurityError(f"Command execution failed: {str(e)}") from e


class InputValidator:
    """Input validation utilities."""
    
    # Maximum lengths for various inputs
    MAX_PROJECT_NAME = 100
    MAX_DESCRIPTION = 1000
    MAX_PROMPT_LENGTH = 10000
    MAX_LANGUAGE_CODE = 10
    
    # Regex patterns
    PROJECT_NAME_PATTERN = re.compile(r'^[\w\s\-\(\)\[\]\{\}\.,]+$')
    LANGUAGE_CODE_PATTERN = re.compile(r'^[a-z]{2,3}(-[A-Z]{2})?$')
    UUID_PATTERN = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
        re.IGNORECASE
    )
    
    @classmethod
    def validate_project_name(cls, name: str) -> str:
        """Validate and sanitize project name."""
        if not name or not name.strip():
            raise SecurityError("Project name cannot be empty")
        
        name = name.strip()
        if len(name) > cls.MAX_PROJECT_NAME:
            raise SecurityError(f"Project name too long (max {cls.MAX_PROJECT_NAME} chars)")
        
        if not cls.PROJECT_NAME_PATTERN.match(name):
            raise SecurityError("Project name contains invalid characters")
        
        return name
    
    @classmethod
    def validate_language_code(cls, code: str) -> str:
        """Validate language code."""
        code = code.strip().lower()
        if not cls.LANGUAGE_CODE_PATTERN.match(code):
            raise SecurityError(f"Invalid language code: {code}")
        return code
    
    @classmethod
    def validate_uuid(cls, uuid_str: str) -> str:
        """Validate UUID format."""
        if not cls.UUID_PATTERN.match(uuid_str):
            raise SecurityError(f"Invalid UUID format: {uuid_str}")
        return uuid_str.lower()
    
    @classmethod
    def validate_prompt(cls, prompt: str) -> str:
        """Validate prompt text."""
        if not prompt or not prompt.strip():
            raise SecurityError("Prompt cannot be empty")
        
        if len(prompt) > cls.MAX_PROMPT_LENGTH:
            raise SecurityError(f"Prompt too long (max {cls.MAX_PROMPT_LENGTH} chars)")
        
        return prompt.strip()
    
    @classmethod
    def sanitize_json_input(cls, data: dict, max_depth: int = 10, 
                            max_keys: int = 1000) -> dict:
        """Sanitize JSON input to prevent DoS."""
        def _sanitize(obj, depth=0):
            if depth > max_depth:
                raise SecurityError("JSON nesting too deep")
            
            if isinstance(obj, dict):
                if len(obj) > max_keys:
                    raise SecurityError("Too many keys in JSON object")
                return {_sanitize(k, depth+1): _sanitize(v, depth+1) for k, v in obj.items()}
            elif isinstance(obj, list):
                if len(obj) > max_keys:
                    raise SecurityError("Too many items in JSON array")
                return [_sanitize(item, depth+1) for item in obj]
            elif isinstance(obj, str):
                if len(obj) > 100000:  # 100KB per string
                    raise SecurityError("String value too long")
                return obj
            elif isinstance(obj, (int, float, bool)) or obj is None:
                return obj
            else:
                raise SecurityError(f"Unsupported JSON type: {type(obj)}")
        
        return _sanitize(data)


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify HMAC signature for webhook payloads."""
    import hmac
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = {}
    
    def check_rate_limit(self, key: str) -> bool:
        """Check if request is within rate limit."""
        import time
        now = time.time()
        
        if key not in self._requests:
            self._requests[key] = []
        
        # Remove old requests
        self._requests[key] = [
            t for t in self._requests[key] 
            if now - t < self.window_seconds
        ]
        
        if len(self._requests[key]) >= self.max_requests:
            return False
        
        self._requests[key].append(now)
        return True
    
    def get_remaining(self, key: str) -> int:
        """Get remaining requests in current window."""
        import time
        now = time.time()
        
        if key not in self._requests:
            return self.max_requests
        
        current = len([
            t for t in self._requests[key] 
            if now - t < self.window_seconds
        ])
        
        return max(0, self.max_requests - current)