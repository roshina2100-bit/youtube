"""
Video Generation Service for the Cinematic Video Studio.
Handles video generation from images, FFmpeg fallback, and silent master creation.
"""

import asyncio
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List
from uuid import UUID

from app.services.project_manager import ProjectManager
from app.workflow.engine import WorkflowEngine
from app.providers.registry import ProviderRegistry
from app.models.provider import ProviderType
from app.models.job import Job, JobType
from app.utils.ffmpeg import FFmpegWrapper
from app.core.config import get_settings
from app.core.logging import log_generation


class VideoGenerationService:
    """Service for video generation and processing."""
    
    def __init__(
        self, 
        project_manager: ProjectManager, 
        workflow_engine: WorkflowEngine,
        provider_registry: ProviderRegistry
    ):
        self.project_manager = project_manager
        self.workflow_engine = workflow_engine
        self.provider_registry = provider_registry
        self._settings = get_settings()
        self.ffmpeg = FFmpegWrapper(self._settings.ffmpeg_path)
    
    async def generate_scene_video(
        self,
        project_id: UUID,
        scene_id: str,
        image_path: str,
        prompt: str,
        negative_prompt: str = "",
        num_frames: int = 25,
        fps: int = 7,
        provider_name: str = "local_python",
        model_name: str = "svd-xt",
    ) -> Dict[str, Any]:
        """Generate video for a scene from an image."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        scene = self.project_manager.load_scene(project_dir, scene_id)
        
        if not scene:
            raise ValueError(f"Scene not found: {scene_id}")
        
        # Get video generation provider
        provider = self.provider_registry.get_provider(
            ProviderType.VIDEO_GENERATION, provider_name, model_name
        )
        
        if not provider:
            await self.provider_registry.load_provider(
                ProviderType.VIDEO_GENERATION, provider_name, model_name
            )
            provider = self.provider_registry.get_provider(
                ProviderType.VIDEO_GENERATION, provider_name, model_name
            )
        
        if not provider or not provider.is_available():
            # Use FFmpeg fallback
            return await self._generate_ffmpeg_fallback(
                project_id, scene_id, image_path, prompt, num_frames, fps
            )
        
        # Generate video using provider
        full_image_path = project_dir / image_path
        if not full_image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        result = await provider.generate(
            image_path=str(full_image_path),
            prompt=prompt,
            negative_prompt=negative_prompt,
            num_frames=num_frames,
            fps=fps,
        )
        
        if not result.success:
            # Fallback to FFmpeg
            return await self._generate_ffmpeg_fallback(
                project_id, scene_id, image_path, prompt, num_frames, fps
            )
        
        # Save video
        video_data = result.data
        video_path = video_data["video_path"]
        
        version = self.project_manager.get_next_version(
            project_dir, f"{scene_id}", "video/scenes"
        )
        
        video_filename = f"{scene_id}_{version}.mp4"
        dest_path = project_dir / "video" / "scenes" / video_filename
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        shutil.move(video_path, dest_path)
        
        # Update scene
        scene.video_path = f"video/scenes/{video_filename}"
        self.project_manager.save_scene(project_dir, scene)
        
        # Save metadata
        from app.models.asset import AssetMetadata, AssetType
        asset = AssetMetadata(
            asset_type=AssetType.SCENE_VIDEO,
            file_path=f"video/scenes/{video_filename}",
            version=version,
            project_id=project_id,
            generator=f"{provider_name}:{model_name}",
            generation_params={
                "num_frames": video_data["num_frames"],
                "fps": video_data["fps"],
                "duration_seconds": video_data["duration_seconds"],
            },
            prompt=prompt,
            negative_prompt=negative_prompt,
            file_size_bytes=dest_path.stat().st_size,
            sha256=self.project_manager.compute_file_hash(dest_path),
            duration_seconds=video_data["duration_seconds"],
        )
        self.project_manager.save_asset_metadata(project_dir, asset)
        
        log_generation(
            None,
            "scene_video",
            f"{provider_name}:{model_name}",
            model_name,
            0,
            scene_id=scene_id,
            version=version,
        )
        
        return {
            "video_path": f"video/scenes/{video_filename}",
            "version": version,
            "metadata": video_data,
        }
    
    async def _generate_ffmpeg_fallback(
        self,
        project_id: UUID,
        scene_id: str,
        image_path: str,
        prompt: str,
        num_frames: int,
        fps: int,
    ) -> Dict[str, Any]:
        """Generate video using FFmpeg (zoom/pan simulation)."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        full_image_path = project_dir / image_path
        
        if not full_image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        version = self.project_manager.get_next_version(
            project_dir, f"{scene_id}", "video/scenes"
        )
        
        video_filename = f"{scene_id}_{version}.mp4"
        output_path = project_dir / "video" / "scenes" / video_filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create video from image with zoom/pan effect
        duration = num_frames / fps
        
        # Use FFmpeg to create video with zoom effect
        await self.ffmpeg.create_video_from_images(
            image_pattern=str(full_image_path),
            output_path=str(output_path),
            fps=fps,
            duration=duration,
        )
        
        # Update scene
        scene = self.project_manager.load_scene(
            self.project_manager.get_project_path(str(project_id)), scene_id
        )
        if scene:
            scene.video_path = f"video/scenes/{video_filename}"
            self.project_manager.save_scene(
                self.project_manager.get_project_path(str(project_id)), scene
            )
        
        # Save metadata
        from app.models.asset import AssetMetadata, AssetType
        asset = AssetMetadata(
            asset_type=AssetType.SCENE_VIDEO,
            file_path=f"video/scenes/{video_filename}",
            version=version,
            project_id=project_id,
            generator="ffmpeg:fallback",
            generation_params={
                "num_frames": num_frames,
                "fps": fps,
                "duration_seconds": duration,
                "fallback": True,
            },
            prompt=prompt,
            file_size_bytes=output_path.stat().st_size,
            sha256=self.project_manager.compute_file_hash(output_path),
            duration_seconds=duration,
        )
        self.project_manager.save_asset_metadata(
            self.project_manager.get_project_path(str(project_id)), asset
        )
        
        return {
            "video_path": f"video/scenes/{video_filename}",
            "version": version,
            "metadata": {
                "num_frames": num_frames,
                "fps": fps,
                "duration_seconds": duration,
                "fallback": True,
            },
        }
    
    async def generate_silent_master(self, project_id: UUID) -> str:
        """Generate silent master video by concatenating all scene videos."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        scenes = self.project_manager.load_scenes_index(project_dir)
        
        scene_videos = []
        for scene_info in scenes:
            scene = self.project_manager.load_scene(project_dir, scene_info["scene_id"])
            if scene and scene.video_path:
                video_path = project_dir / scene.video_path
                if video_path.exists():
                    scene_videos.append(str(video_path))
        
        if not scene_videos:
            raise ValueError("No scene videos found to create silent master")
        
        version = self.project_manager.get_next_version(
            project_dir, "master", "video/silent_master"
        )
        
        output_path = project_dir / "video" / "silent_master" / f"master_{version}.mp4"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        await self.ffmpeg.concat_videos(scene_videos, str(output_path))
        
        # Save metadata
        from app.models.asset import AssetMetadata, AssetType
        asset = AssetMetadata(
            asset_type=AssetType.SILENT_MASTER,
            file_path=f"video/silent_master/master_{version}.mp4",
            version=version,
            project_id=project_id,
            generator="ffmpeg:concat",
            generation_params={
                "scene_count": len(scene_videos),
            },
            file_size_bytes=output_path.stat().st_size,
            sha256=self.project_manager.compute_file_hash(output_path),
        )
        self.project_manager.save_asset_metadata(project_dir, asset)
        
        return f"video/silent_master/master_{version}.mp4"
    
    def get_silent_master(self, project_id: UUID) -> Optional[str]:
        """Get latest silent master video path."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        master_dir = project_dir / "video" / "silent_master"
        
        if not master_dir.exists():
            return None
        
        masters = list(master_dir.glob("master_v*.mp4"))
        if not masters:
            return None
        
        latest = max(masters, key=lambda f: f.stem)
        return f"video/silent_master/{latest.name}"
    
    async def create_preview(
        self,
        project_id: UUID,
        language: str,
        include_subtitles: bool = True,
    ) -> str:
        """Create preview video for a language."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        
        # Get silent master
        silent_master = self.get_silent_master(project_id)
        if not silent_master:
            raise ValueError("Silent master not found")
        
        # Get master audio for language
        master_audio = project_dir / "audio" / language / "master_audio.wav"
        if not master_audio.exists():
            raise ValueError(f"Master audio not found for {language}")
        
        version = self.project_manager.get_next_version(
            project_dir, f"preview_{language}", "video/previews"
        )
        
        output_path = project_dir / "video" / "previews" / f"preview_{language}_{version}.mp4"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Mux video and audio
        await self.ffmpeg.mux_video_audio(
            video_path=str(project_dir / silent_master),
            audio_path=str(master_audio),
            output_path=str(output_path),
        )
        
        # Add subtitles if requested
        if include_subtitles:
            # Would add subtitle burning here
            pass
        
        return f"video/previews/preview_{language}_{version}.mp4"