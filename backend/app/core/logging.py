"""
Logging configuration for the Cinematic Video Studio backend.
Structured JSON logging with project-specific and application logs.
"""

import json
import logging
import logging.handlers
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
import uuid


class JSONFormatter(logging.Formatter):
    """JSON log formatter with structured fields."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields if present
        for key, value in record.__dict__.items():
            if key not in {
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "message", "name", "pathname", "process", "processName",
                "relativeCreated", "thread", "threadName", "exc_info",
                "exc_text", "stack_info"
            }:
                # Sanitize sensitive data
                if key.lower() in ("api_key", "password", "token", "secret"):
                    log_entry[key] = "***REDACTED***"
                else:
                    log_entry[key] = value
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, ensure_ascii=False)


class ProjectLogFilter(logging.Filter):
    """Filter to add project_id to log records."""
    
    def __init__(self, project_id: Optional[str] = None):
        super().__init__()
        self.project_id = project_id
    
    def filter(self, record: logging.LogRecord) -> bool:
        if self.project_id:
            record.project_id = self.project_id
        return True


def setup_logging(log_level: str = "INFO", debug: bool = False) -> None:
    """Configure application logging."""
    
    # Determine log level
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler (human-readable in debug, JSON in production)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    if debug:
        console_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    else:
        console_formatter = JSONFormatter()
    
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # Application log file (rotating)
    app_log_dir = Path("application/logs")
    app_log_dir.mkdir(parents=True, exist_ok=True)
    
    app_file_handler = logging.handlers.RotatingFileHandler(
        app_log_dir / "application.jsonl",
        maxBytes=10_000_000,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    app_file_handler.setLevel(level)
    app_file_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(app_file_handler)
    
    # Error log file (separate)
    error_file_handler = logging.handlers.RotatingFileHandler(
        app_log_dir / "errors.jsonl",
        maxBytes=10_000_000,
        backupCount=5,
        encoding="utf-8"
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(error_file_handler)
    
    # Suppress noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_project_logger(project_id: str, project_root: Path) -> logging.Logger:
    """Get a logger for a specific project with project-specific file handler."""
    logger = logging.getLogger(f"project.{project_id}")
    
    # Avoid duplicate handlers
    if any(isinstance(h, logging.handlers.RotatingFileHandler) and 
           "projects" in str(h.baseFilename) for h in logger.handlers):
        return logger
    
    # Project log directory
    project_log_dir = project_root / project_id / "logs"
    project_log_dir.mkdir(parents=True, exist_ok=True)
    
    # Project log file (rotating)
    project_file_handler = logging.handlers.RotatingFileHandler(
        project_log_dir / f"{datetime.utcnow().strftime('%Y-%m-%d')}.jsonl",
        maxBytes=10_000_000,
        backupCount=10,
        encoding="utf-8"
    )
    project_file_handler.setFormatter(JSONFormatter())
    project_file_handler.addFilter(ProjectLogFilter(project_id))
    logger.addHandler(project_file_handler)
    
    # Don't propagate to root (avoid duplicate console output)
    logger.propagate = False
    
    return logger


def log_job_start(logger: logging.Logger, job_id: str, job_type: str, **kwargs) -> None:
    """Log job start with structured data."""
    logger.info(
        f"Job started: {job_type}",
        extra={
            "job_id": job_id,
            "job_type": job_type,
            "event": "job_start",
            **kwargs
        }
    )


def log_job_progress(logger: logging.Logger, job_id: str, progress: int, 
                     step: str, **kwargs) -> None:
    """Log job progress with structured data."""
    logger.info(
        f"Job progress: {progress}% - {step}",
        extra={
            "job_id": job_id,
            "progress": progress,
            "current_step": step,
            "event": "job_progress",
            **kwargs
        }
    )


def log_job_complete(logger: logging.Logger, job_id: str, job_type: str, 
                     duration_seconds: float, **kwargs) -> None:
    """Log job completion with structured data."""
    logger.info(
        f"Job completed: {job_type}",
        extra={
            "job_id": job_id,
            "job_type": job_type,
            "duration_seconds": duration_seconds,
            "event": "job_complete",
            **kwargs
        }
    )


def log_job_error(logger: logging.Logger, job_id: str, job_type: str, 
                  error: Exception, **kwargs) -> None:
    """Log job error with structured data."""
    logger.error(
        f"Job failed: {job_type} - {str(error)}",
        extra={
            "job_id": job_id,
            "job_type": job_type,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "event": "job_error",
            **kwargs
        },
        exc_info=True
    )


def log_model_load(logger: logging.Logger, model_name: str, provider: str, 
                   device: str, vram_mb: Optional[float] = None, **kwargs) -> None:
    """Log model loading with structured data."""
    logger.info(
        f"Model loaded: {model_name}",
        extra={
            "model_name": model_name,
            "provider": provider,
            "device": device,
            "vram_mb": vram_mb,
            "event": "model_load",
            **kwargs
        }
    )


def log_model_unload(logger: logging.Logger, model_name: str, provider: str, **kwargs) -> None:
    """Log model unloading with structured data."""
    logger.info(
        f"Model unloaded: {model_name}",
        extra={
            "model_name": model_name,
            "provider": provider,
            "event": "model_unload",
            **kwargs
        }
    )


def log_generation(logger: logging.Logger, operation: str, provider: str, 
                   model: str, duration_seconds: float, **kwargs) -> None:
    """Log AI generation operation with structured data."""
    logger.info(
        f"Generation completed: {operation}",
        extra={
            "operation": operation,
            "provider": provider,
            "model": model,
            "duration_seconds": duration_seconds,
            "event": "generation",
            **kwargs
        }
    )


def log_file_operation(logger: Optional[logging.Logger], operation: str, file_path: str,
                       file_size: Optional[int] = None, sha256: Optional[str] = None, **kwargs) -> None:
    """Log file operation with structured data."""
    if logger is None:
        logger = logging.getLogger(__name__)
    logger.info(
        f"File {operation}: {file_path}",
        extra={
            "operation": operation,
            "file_path": file_path,
            "file_size_bytes": file_size,
            "sha256": sha256,
            "event": "file_operation",
            **kwargs
        }
    )