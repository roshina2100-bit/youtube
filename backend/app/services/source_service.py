"""
Source Service for the Cinematic Video Studio.
Handles source media import, validation, and metadata extraction.
"""

import asyncio
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List
from uuid import UUID

from app.services.project_manager import ProjectManager
from app.workflow.engine import WorkflowEngine
from app.models.job import Job, JobType
from app.core.config import get_settings
from app.core.security import validate_file_extension, sanitize_filename
from app.utils.ffmpeg import FFmpegWrapper


class SourceService:
    """Service for source media management."""
    
    VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv', '.m4v'}
    AUDIO_EXTENSIONS = {'.wav', '.mp3', '.flac', '.ogg', '.aac', '.m4a', '.wma'}
    TRANSCRIPT_EXTENSIONS = {'.txt', '.srt', '.vtt', '.json'}
    ALL_MEDIA_EXTENSIONS = VIDEO_EXTENSIONS | AUDIO_EXTENSIONS | TRANSCRIPT_EXTENSIONS
    
    def __init__(self, project_manager: ProjectManager, workflow_engine: WorkflowEngine):
        self.project_manager = project_manager
        self.workflow_engine = workflow_engine
        self._settings = get_settings()
        self.ffmpeg = FFmpegWrapper(self._settings.ffmpeg_path)
    
    async def import_local_file(
        self,
        project_id: UUID,
        file_path: Path,
        original_filename: str,
    ) -> Dict[str, Any]:
        """Import a local media file."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        source_dir = project_dir / "source" / "source_media"
        source_dir.mkdir(parents=True, exist_ok=True)
        
        # Validate file
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        filename = sanitize_filename(original_filename)
        if not self._is_valid_media_file(filename):
            raise ValueError(f"Unsupported file type: {filename}")
        
        # Copy file to project
        dest_path = source_dir / filename
        shutil.copy2(file_path, dest_path)
        
        # Probe media for metadata
        metadata = await self.ffmpeg.probe(str(dest_path))
        video_info = await self.ffmpeg.get_video_info(str(dest_path))
        audio_info = await self.ffmpeg.get_audio_info(str(dest_path))
        duration = video_info.get("duration") or audio_info.get("duration") or 0
        
        # Update project manifest
        project = self.project_manager.load_project(str(project_id))
        project.source = {
            "type": "local_file",
            "path": f"source/source_media/{filename}",
            "original_filename": original_filename,
            "duration_seconds": duration,
            "metadata": metadata
        }
        self.project_manager.save_project(self.project_manager.get_project_path(str(project_id)), project)
        
        return {
            "type": "local_file",
            "path": f"source/source_media/{filename}",
            "original_filename": original_filename,
            "duration_seconds": duration,
            "metadata": metadata
        }
    
    async def import_transcript(
        self,
        project_id: UUID,
        content: str,
        format: str = "txt",
    ) -> Dict[str, Any]:
        """Import transcript content."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        transcript_dir = project_dir / "transcript"
        transcript_dir.mkdir(parents=True, exist_ok=True)
        
        # Save original transcript
        original_path = transcript_dir / "original.txt"
        original_path.write_text(content, encoding='utf-8')
        
        # Save format info
        import json
        (transcript_dir / "original.json").write_text(
            json.dumps({"content": content, "format": "txt"}, indent=2),
            encoding='utf-8'
        )
        
        # Update project manifest
        project = self.project_manager.load_project(str(project_id))
        project.source = {
            "type": "transcript",
            "path": "transcript/original.txt",
            "original_filename": "transcript.txt",
            "duration_seconds": 0,
            "metadata": {}
        }
        self.project_manager.save_project(project_dir, project)
        
        return {
            "type": "transcript",
            "path": "transcript/original.txt",
            "original_filename": "transcript.txt",
            "duration_seconds": 0,
            "metadata": {}
        }
    
    def _is_valid_media_file(self, filename: str) -> bool:
        """Check if file extension is valid."""
        ext = Path(filename).suffix.lower()
        return ext in self.ALL_MEDIA_EXTENSIONS
    
    async def get_media_info(self, project_id: UUID) -> Optional[Dict[str, Any]]:
        """Get media information for a project."""
        try:
            project = self.project_manager.load_project(str(project_id))
        except FileNotFoundError:
            return None
        
        source = project.source
        if not source.get("path"):
            return None
        
        project_dir = self.project_manager.get_project_path(str(project_id))
        full_path = project_dir / source["path"]
        
        if not full_path.exists():
            return None
        
        metadata = await self.ffmpeg.probe(str(full_path))
        video_info = await self.ffmpeg.get_video_info(str(full_path))
        audio_info = await self.ffmpeg.get_audio_info(str(full_path))
        
        return {
            "path": source["path"],
            "original_filename": source["original_filename"],
            "duration_seconds": source["duration_seconds"],
            "metadata": metadata,
            "video_info": video_info,
            "audio_info": audio_info,
        }
    
    async def delete_source(self, project_id: UUID) -> bool:
        """Delete source media from project."""
        try:
            project_dir = self.project_manager.get_project_path(str(project_id))
            project = self.project_manager.load_project(str(project_id))
        except FileNotFoundError:
            return False
        
        source_path = project.source.get("path")
        if source_path:
            full_path = project_dir / source_path
            if full_path.exists():
                full_path.unlink()
        
        # Reset source in project
        project.source = {
            "type": "",
            "path": "",
            "original_filename": "",
            "duration_seconds": 0,
            "metadata": {}
        }
        self.project_manager.save_project(project_dir, project)
        
        return True