"""
Audio Generation Service for the Cinematic Video Studio.
Handles TTS, music generation, SFX, and audio mixing.
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


class AudioGenerationService:
    """Service for audio generation and processing."""
    
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
    
    async def generate_tts(
        self,
        project_id: UUID,
        scene_id: str,
        language: str,
        provider_name: str = "local_python",
        model_name: str = "xtts-v2",
    ) -> Dict[str, Any]:
        """Generate TTS audio for a scene in a language."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        scene = self.project_manager.load_scene(project_dir, scene_id)
        
        if not scene:
            raise ValueError(f"Scene not found: {scene_id}")
        
        # Get translation workspace for language
        workspace = self.project_manager.load_translation(project_dir, language)
        if not workspace:
            raise ValueError(f"Translation not found for {language}")
        
        scene_translation = workspace.get_scene_translation(scene_id)
        if not scene_translation:
            raise ValueError(f"Scene translation not found for {scene_id} in {language}")
        
        # Get TTS provider
        provider = self.provider_registry.get_provider(
            ProviderType.TTS, provider_name, model_name
        )
        
        if not provider:
            await self.provider_registry.load_provider(
                ProviderType.TTS, provider_name, model_name
            )
            provider = self.provider_registry.get_provider(
                ProviderType.TTS, provider_name, model_name
            )
        
        if not provider or not provider.is_available():
            raise RuntimeError(f"TTS provider not available: {provider_name}:{model_name}")
        
        # Generate narration
        narration_text = scene_translation.narration
        voice_prompt = workspace.voice_prompts.get("narrator", "Narrator voice")
        
        narration_result = await provider.synthesize(
            text=narration_text,
            voice_id=voice_prompt,
            language=language,
        )
        
        if not narration_result.success:
            raise RuntimeError(f"TTS generation failed: {narration_result.error}")
        
        # Save narration
        narration_data = narration_result.data
        narration_path = narration_data["audio_path"]
        
        version = self.project_manager.get_next_version(
            self.project_manager.get_project_path(str(project_id)), 
            f"{scene_id}_narration_{language}", 
            "audio/narration"
        )
        
        narration_filename = f"{scene_id}_narration_{language}_{version}.wav"
        dest_path = project_dir / "audio" / language / "narration" / narration_filename
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        shutil.move(narration_path, dest_path)
        
        # Generate dialogue for each character
        dialogue_files = []
        for dlg in scene_translation.dialogue:
            speaker = dlg.get("speaker", "")
            text = dlg.get("text", "")
            if not text:
                continue
            
            voice_prompt = workspace.voice_prompts.get(speaker, "Default voice")
            
            dlg_result = await provider.synthesize(
                text=text,
                voice_id=voice_prompt,
                language=language,
            )
            
            if dlg_result.success:
                dlg_data = dlg_result.data
                dlg_path = dlg_data["audio_path"]
                
                dlg_version = self.project_manager.get_next_version(
                    self.project_manager.get_project_path(str(project_id)), 
                    f"{scene_id}_dlg_{speaker}_{language}", 
                    "audio/dialogue"
                )
                
                dlg_filename = f"{scene_id}_dlg_{speaker}_{language}_{dlg_version}.wav"
                dlg_dest = project_dir / "audio" / language / "dialogue" / dlg_filename
                dlg_dest.parent.mkdir(parents=True, exist_ok=True)
                
                shutil.move(dlg_path, dlg_dest)
                dialogue_files.append({
                    "speaker": speaker,
                    "path": f"audio/{language}/dialogue/{dlg_filename}",
                })
        
        return {
            "narration": f"audio/{language}/narration/{narration_filename}",
            "dialogue": dialogue_files,
        }
    
    async def generate_music(
        self,
        project_id: UUID,
        scene_id: str,
        language: str,
        provider_name: str = "local_python",
        model_name: str = "musicgen-large",
    ) -> Dict[str, Any]:
        """Generate music for a scene in a language."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        scene = self.project_manager.load_scene(project_dir, scene_id)
        
        if not scene:
            raise ValueError(f"Scene not found: {scene_id}")
        
        # Get translation workspace for language
        workspace = self.project_manager.load_translation(project_dir, language)
        if not workspace:
            raise ValueError(f"Translation not found for {language}")
        
        # Get music provider
        provider = self.provider_registry.get_provider(
            ProviderType.MUSIC_GENERATION, provider_name, model_name
        )
        
        if not provider:
            await self.provider_registry.load_provider(
                ProviderType.MUSIC_GENERATION, provider_name, model_name
            )
            provider = self.provider_registry.get_provider(
                ProviderType.MUSIC_GENERATION, provider_name, model_name
            )
        
        if not provider or not provider.is_available():
            raise RuntimeError(f"Music provider not available: {provider_name}:{model_name}")
        
        # Get music prompt
        music_prompt = workspace.music_prompts.get(scene_id, scene.music.style)
        duration = scene.music.duration_seconds or 30.0
        
        result = await provider.generate(
            prompt=music_prompt,
            duration=duration,
        )
        
        if not result.success:
            raise RuntimeError(f"Music generation failed: {result.error}")
        
        # Save music
        music_data = result.data
        music_path = music_data["audio_path"]
        
        version = self.project_manager.get_next_version(
            self.project_manager.get_project_path(str(project_id)), 
            f"{scene_id}_music_{language}", 
            "audio/music"
        )
        
        music_filename = f"{scene_id}_music_{language}_{version}.wav"
        dest_path = project_dir / "audio" / language / "music" / music_filename
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        shutil.move(music_path, dest_path)
        
        return {
            "music": f"audio/{language}/music/{music_filename}",
        }
    
    async def generate_sfx(
        self,
        project_id: UUID,
        scene_id: str,
        language: str,
        provider_name: str = "local_python",
        model_name: str = "audioldm2",
    ) -> Dict[str, Any]:
        """Generate sound effects for a scene in a language."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        scene = self.project_manager.load_scene(project_dir, scene_id)
        
        if not scene:
            raise ValueError(f"Scene not found: {scene_id}")
        
        # Get SFX provider
        provider = self.provider_registry.get_provider(
            ProviderType.SFX_GENERATION, provider_name, model_name
        )
        
        if not provider:
            await self.provider_registry.load_provider(
                ProviderType.SFX_GENERATION, provider_name, model_name
            )
            provider = self.provider_registry.get_provider(
                ProviderType.SFX_GENERATION, provider_name, model_name
            )
        
        if not provider or not provider.is_available():
            raise RuntimeError(f"SFX provider not available: {provider_name}:{model_name}")
        
        sfx_files = []
        for sfx_config in scene.sound_effects:
            prompt = sfx_config.description
            duration = sfx_config.duration or 5.0
            
            result = await provider.generate(
                prompt=prompt,
                duration=duration,
            )
            
            if result.success:
                sfx_data = result.data
                sfx_path = sfx_data["audio_path"]
                
                version = self.project_manager.get_next_version(
                    self.project_manager.get_project_path(str(project_id)), 
                    f"{scene_id}_sfx_{language}", 
                    "audio/sfx"
                )
                
                sfx_filename = f"{scene_id}_sfx_{language}_{version}.wav"
                dest_path = project_dir / "audio" / language / "sfx" / sfx_filename
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                
                shutil.move(sfx_path, dest_path)
                sfx_files.append(f"audio/{language}/sfx/{sfx_filename}")
        
        return {
            "sfx": sfx_files,
        }
    
    async def mix_audio(
        self,
        project_id: UUID,
        language: str,
    ) -> str:
        """Mix all audio tracks for a language into master audio."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        audio_dir = project_dir / "audio" / language
        
        # Collect all audio files
        narration_files = list((audio_dir / "narration").glob("*.wav")) if (audio_dir / "narration").exists() else []
        dialogue_files = list((audio_dir / "dialogue").glob("*.wav")) if (audio_dir / "dialogue").exists() else []
        music_files = list((audio_dir / "music").glob("*.wav")) if (audio_dir / "music").exists() else []
        sfx_files = list((audio_dir / "sfx").glob("*.wav")) if (audio_dir / "sfx").exists() else []
        
        all_files = []
        volumes = []
        
        # Narration at full volume
        for f in narration_files:
            all_files.append(str(f))
            volumes.append(1.0)
        
        # Dialogue at full volume
        for f in dialogue_files:
            all_files.append(str(f))
            volumes.append(1.0)
        
        # Music at lower volume
        for f in music_files:
            all_files.append(str(f))
            volumes.append(0.3)
        
        # SFX at medium volume
        for f in sfx_files:
            all_files.append(str(f))
            volumes.append(0.5)
        
        if not all_files:
            raise ValueError("No audio files to mix")
        
        # Mix audio
        master_path = audio_dir / "master_audio.wav"
        await self.ffmpeg.mix_audio(
            audio_paths=all_files,
            output_path=str(master_path),
            volumes=volumes,
            normalize=True,
        )
        
        return f"audio/{language}/master_audio.wav"
    
    async def create_master_audio(
        self,
        project_id: UUID,
        language: str,
    ) -> str:
        """Create master audio for a language by mixing all tracks."""
        return await self.mix_audio(project_id, language)
    
    def get_language_audio(self, project_id: UUID, language: str) -> Dict[str, Any]:
        """Get audio files for a language."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        audio_dir = project_dir / "audio" / language
        
        if not audio_dir.exists():
            raise FileNotFoundError(f"No audio found for {language}")
        
        audio_files = {}
        for subdir in ["narration", "dialogue", "music", "sfx"]:
            subdir_path = audio_dir / subdir
            if subdir_path.exists():
                audio_files[subdir] = [f.name for f in subdir_path.iterdir() if f.is_file()]
        
        master_path = audio_dir / "master_audio.wav"
        if master_path.exists():
            audio_files["master"] = "master_audio.wav"
        
        return {"language": language, "audio_files": audio_files}