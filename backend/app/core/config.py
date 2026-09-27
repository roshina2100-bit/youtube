"""
Configuration management for the Cinematic Video Studio backend.
Uses Pydantic Settings for environment variable and config file management.
"""

from pathlib import Path
from typing import Optional, List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import yaml


class ModelConfig(BaseSettings):
    """Configuration for a single AI model."""
    provider: str = "local_python"
    backend: str = "transformers"
    model_path: str = ""
    device: str = "cuda"
    torch_dtype: str = "float16"
    load_in_4bit: bool = False
    load_in_8bit: bool = False
    trust_remote_code: bool = False
    
    # Generation config (for LLM)
    max_new_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 0.9
    do_sample: bool = True
    
    # Transcription config
    compute_type: str = "float16"
    cpu_threads: int = 4
    num_workers: int = 1
    download_root: Optional[str] = None
    
    # Translation config
    src_lang: str = "auto"
    tgt_lang: str = "eng_Latn"
    
    # Image generation config
    refiner_path: Optional[str] = None
    variant: str = "fp16"
    use_safetensors: bool = True
    enable_xformers: bool = True
    enable_cpu_offload: bool = False
    enable_sequential_cpu_offload: bool = False
    vae_path: Optional[str] = None
    scheduler: str = "euler_ancestral"
    default_steps: int = 30
    default_guidance_scale: float = 7.5
    default_width: int = 1024
    default_height: int = 1024
    
    # Video generation config
    num_frames: int = 25
    fps: int = 7
    motion_bucket_id: int = 127
    noise_aug_strength: float = 0.02
    decode_chunk_size: int = 8
    
    # TTS config
    speaker_wav: Optional[str] = None
    language: str = "en"
    speed: float = 1.0
    
    # Music/SFX config
    max_duration: float = 30.0


class NotebookLMConfig(BaseSettings):
    """NotebookLM/API external provider configuration."""
    enabled: bool = False
    api_key: str = ""
    endpoint: str = ""
    project_id: str = ""
    model: str = ""
    timeout_seconds: int = 300
    max_retries: int = 3


class Settings(BaseSettings):
    """Application settings loaded from environment and config files."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # Application
    app_name: str = "Cinematic Video Studio"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    
    # Project storage
    project_root: str = "projects"
    
    # Security
    secret_key: str = ""
    cors_origins: List[str] = Field(default_factory=lambda: ["http://localhost:4200", "http://127.0.0.1:4200"])
    max_upload_size: int = 524288000  # 500MB
    
    # FFmpeg
    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"
    
    # Performance
    max_concurrent_gpu_jobs: int = 1
    enable_cpu_fallback: bool = True
    model_idle_timeout: int = 300
    
    # Provider defaults
    ai_default_provider: str = "local_python"
    ai_allow_external_provider: bool = True
    ai_fallback_to_local: bool = False
    
    # NotebookLM
    notebooklm: NotebookLMConfig = Field(default_factory=NotebookLMConfig)
    
    # Models (loaded from models.yaml)
    models: dict = Field(default_factory=dict)
    
    # Test mode
    test_mode: bool = False
    test_fixtures_dir: str = "tests/fixtures/project"
    
    @field_validator("project_root", mode="before")
    @classmethod
    def expand_project_root(cls, v: str) -> str:
        return str(Path(v).expanduser().resolve())
    
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | List[str]) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v


def load_models_config(config_path: Optional[Path] = None) -> dict:
    """Load model configuration from YAML file."""
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "config" / "models.yaml"
    
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the global settings instance (singleton)."""
    global _settings
    if _settings is None:
        # Load models config
        models_config = load_models_config()
        
        # Create settings with models config
        _settings = Settings(models=models_config)
    return _settings


def reload_settings() -> Settings:
    """Reload settings from environment and config files."""
    global _settings
    _settings = None
    return get_settings()