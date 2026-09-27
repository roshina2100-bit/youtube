"""
Render Service for the Cinematic Video Studio.
Handles final video rendering, muxing, subtitle burning, and export packaging.
"""

import asyncio
import shutil
import zipfile
from pathlib import Path
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime

from app.services.project_manager import ProjectManager
from app.workflow.engine import WorkflowEngine
from app.utils.ffmpeg import FFmpegWrapper
from app.core.config import get_settings
from app.core.logging import log_generation


class RenderService:
    """Service for final video rendering and export."""
    
    def __init__(
        self, 
        project_manager: ProjectManager, 
        workflow_engine: WorkflowEngine
    ):
        self.project_manager = project_manager
        self.workflow_engine = workflow_engine
        self._settings = get_settings()
        self.ffmpeg = FFmpegWrapper(self._settings.ffmpeg_path)
    
    async def render_final_video(
        self,
        project_id: UUID,
        language: str,
        include_subtitles: bool = True,
        subtitle_style: Optional[str] = None,
    ) -> str:
        """Render final video for a language by muxing silent master with master audio."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        
        # Get silent master
        silent_master = self._get_silent_master(project_dir)
        if not silent_master:
            raise ValueError("Silent master not found. Generate silent master first.")
        
        # Get master audio for language
        master_audio = project_dir / "audio" / language / "master_audio.wav"
        if not master_audio.exists():
            raise ValueError(f"Master audio not found for {language}")
        
        # Create output path
        version = self.project_manager.get_next_version(
            project_dir, f"final_{language}", "output"
        )
        
        output_path = project_dir / "output" / language / f"final_{version}.mp4"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Mux video and audio
        await self.ffmpeg.mux_video_audio(
            video_path=str(project_dir / silent_master),
            audio_path=str(master_audio),
            output_path=str(output_path),
        )
        
        # Add subtitles if requested
        if include_subtitles:
            subtitle_path = await self._generate_subtitles(project_id, language)
            if subtitle_path:
                await self._burn_subtitles(output_path, subtitle_path, subtitle_style)
        
        # Save metadata
        from app.models.asset import AssetMetadata, AssetType
        asset = AssetMetadata(
            asset_type=AssetType.FINAL_VIDEO,
            file_path=f"output/{language}/final_{version}.mp4",
            version=version,
            project_id=project_id,
            generator="ffmpeg:mux",
            generation_params={
                "language": language,
                "include_subtitles": include_subtitles,
                "silent_master": silent_master,
                "master_audio": f"audio/{language}/master_audio.wav",
            },
            file_size_bytes=output_path.stat().st_size,
            sha256=self.project_manager.compute_file_hash(output_path),
        )
        self.project_manager.save_asset_metadata(project_dir, asset)
        
        return f"output/{language}/final_{version}.mp4"
    
    async def render_all_languages(
        self,
        project_id: UUID,
        include_subtitles: bool = True,
    ) -> Dict[str, str]:
        """Render final videos for all target languages."""
        project = self.project_manager.load_project(str(project_id))
        results = {}
        
        for language in project.target_languages:
            try:
                output = await self.render_final_video(
                    project_id, language, include_subtitles
                )
                results[language] = output
            except Exception as e:
                results[language] = f"ERROR: {str(e)}"
        
        return results
    
    def _get_silent_master(self, project_dir: Path) -> Optional[str]:
        """Get latest silent master video path."""
        master_dir = project_dir / "video" / "silent_master"
        
        if not master_dir.exists():
            return None
        
        masters = list(master_dir.glob("master_v*.mp4"))
        if not masters:
            return None
        
        latest = max(masters, key=lambda f: f.stem)
        return f"video/silent_master/{latest.name}"
    
    async def _generate_subtitles(self, project_id: UUID, language: str) -> Optional[str]:
        """Generate subtitle file for a language."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        
        # Load translation workspace
        workspace = self.project_manager.load_translation(project_dir, language)
        if not workspace:
            return None
        
        # Generate SRT format subtitles
        subtitle_lines = []
        subtitle_index = 1
        
        scenes = self.project_manager.load_scenes_index(project_dir)
        for scene_info in scenes:
            scene = self.project_manager.load_scene(project_dir, scene_info["scene_id"])
            if not scene:
                continue
            
            translation = workspace.get_scene_translation(scene.scene_id)
            if not translation:
                continue
            
            # Add narration as subtitle
            if translation.narration:
                start_time = self._format_srt_time(scene.duration_seconds * 0)  # Would need actual timing
                end_time = self._format_srt_time(scene.duration_seconds)
                
                subtitle_lines.append(str(subtitle_index))
                subtitle_lines.append(f"{start_time} --> {end_time}")
                subtitle_lines.append(translation.narration)
                subtitle_lines.append("")
                subtitle_index += 1
            
            # Add dialogue as subtitles
            for dlg in translation.dialogue:
                if dlg.get("text"):
                    subtitle_lines.append(str(subtitle_index))
                    subtitle_lines.append(f"{start_time} --> {end_time}")
                    speaker = translation.character_names.get(dlg.get("speaker", ""), dlg.get("speaker", ""))
                    subtitle_lines.append(f"{speaker}: {dlg['text']}")
                    subtitle_lines.append("")
                    subtitle_index += 1
        
        if not subtitle_lines:
            return None
        
        # Save SRT file
        subtitle_dir = project_dir / "output" / language
        subtitle_dir.mkdir(parents=True, exist_ok=True)
        
        subtitle_path = subtitle_dir / f"subtitles_{language}.srt"
        subtitle_path.write_text("\n".join(subtitle_lines), encoding="utf-8")
        
        return str(subtitle_path.relative_to(project_dir))
    
    def _format_srt_time(self, seconds: float) -> str:
        """Format seconds as SRT time (HH:MM:SS,mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    async def _burn_subtitles(
        self, 
        video_path: Path, 
        subtitle_path: str, 
        style: Optional[str] = None
    ) -> None:
        """Burn subtitles into video."""
        # Create temporary output
        temp_path = video_path.with_suffix(".temp.mp4")
        
        await self.ffmpeg.add_subtitles(
            video_path=str(video_path),
            subtitle_path=subtitle_path,
            output_path=str(temp_path),
            subtitle_style=style,
        )
        
        # Replace original
        shutil.move(str(temp_path), str(video_path))
    
    async def export_project(
        self,
        project_id: UUID,
        format: str = "zip",
        include_types: List[str] = [],
        languages: List[str] = [],
        approved_only: bool = True,
    ) -> str:
        """Export project as package."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        project = self.project_manager.load_project(str(project_id))
        
        # Determine what to include
        if not include_types:
            include_types = [
                "project_manifest",
                "transcript",
                "story",
                "characters",
                "scenes",
                "translations",
                "prompts",
                "images",
                "videos",
                "audio",
                "outputs",
            ]
        
        if not languages:
            languages = project.target_languages
        
        # Create export package
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        export_name = f"{project.name}_{timestamp}.{format}"
        export_path = project_dir / "exports" / export_name
        export_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format == "zip":
            with zipfile.ZipFile(export_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                # Add project manifest
                zf.write(project_dir / "project.json", "project.json")
                
                # Add selected file types
                if "transcript" in include_types:
                    self._add_directory_to_zip(zf, project_dir / "transcript", "transcript")
                
                if "story" in include_types:
                    self._add_directory_to_zip(zf, project_dir / "story", "story")
                
                if "characters" in include_types:
                    self._add_directory_to_zip(zf, project_dir / "characters", "characters")
                
                if "scenes" in include_types:
                    self._add_directory_to_zip(zf, project_dir / "scenes", "scenes")
                
                if "translations" in include_types:
                    for lang in languages:
                        lang_dir = project_dir / "languages" / lang
                        if lang_dir.exists():
                            self._add_directory_to_zip(zf, lang_dir, f"languages/{lang}")
                
                if "prompts" in include_types:
                    self._add_directory_to_zip(zf, project_dir / "prompts", "prompts")
                
                if "images" in include_types:
                    self._add_directory_to_zip(zf, project_dir / "images", "images")
                
                if "videos" in include_types:
                    self._add_directory_to_zip(zf, project_dir / "video", "video")
                
                if "audio" in include_types:
                    for lang in languages:
                        audio_dir = project_dir / "audio" / lang
                        if audio_dir.exists():
                            self._add_directory_to_zip(zf, audio_dir, f"audio/{lang}")
                
                if "outputs" in include_types:
                    for lang in languages:
                        output_dir = project_dir / "output" / lang
                        if output_dir.exists():
                            self._add_directory_to_zip(zf, output_dir, f"output/{lang}")
        
        # Save export metadata
        from app.models.asset import AssetMetadata, AssetType
        asset = AssetMetadata(
            asset_type=AssetType.EXPORT,
            file_path=f"exports/{export_name}",
            version="v001",
            project_id=project_id,
            generator="export_service",
            generation_params={
                "format": format,
                "include_types": include_types,
                "languages": languages,
                "approved_only": approved_only,
            },
            file_size_bytes=export_path.stat().st_size,
            sha256=self.project_manager.compute_file_hash(export_path),
        )
        self.project_manager.save_asset_metadata(project_dir, asset)
        
        return f"exports/{export_name}"
    
    def _add_directory_to_zip(self, zf: zipfile.ZipFile, dir_path: Path, arc_prefix: str) -> None:
        """Add all files in a directory to zip."""
        for file_path in dir_path.rglob("*"):
            if file_path.is_file():
                arc_name = f"{arc_prefix}/{file_path.relative_to(dir_path)}"
                zf.write(file_path, arc_name)
    
    def get_output_videos(self, project_id: UUID) -> List[Dict[str, Any]]:
        """List all rendered output videos."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        output_dir = project_dir / "output"
        
        if not output_dir.exists():
            return []
        
        outputs = []
        for lang_dir in output_dir.iterdir():
            if lang_dir.is_dir():
                final_video = lang_dir / "final.mp4"
                if final_video.exists():
                    stat = final_video.stat()
                    outputs.append({
                        "language": lang_dir.name,
                        "path": f"output/{lang_dir.name}/final.mp4",
                        "size_bytes": stat.st_size,
                        "modified": stat.st_mtime
                    })
        
        return outputs
    
    def get_exports(self, project_id: UUID) -> List[Dict[str, Any]]:
        """List all export packages for a project."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        exports_dir = project_dir / "exports"
        
        if not exports_dir.exists():
            return []
        
        exports = []
        for export_file in exports_dir.iterdir():
            if export_file.is_file():
                stat = export_file.stat()
                exports.append({
                    "filename": export_file.name,
                    "path": f"exports/{export_file.name}",
                    "size_bytes": stat.st_size,
                    "modified": stat.st_mtime
                })
        
        return exports