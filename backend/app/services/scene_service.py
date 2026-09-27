"""
Scene Service for the Cinematic Video Studio.
Handles scene generation, cinematic prompt engineering, and scene management.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.models.scene import (
    Scene, SceneStatus, CameraConfig, LensConfig, LightingConfig,
    MusicConfig, SFXConfig, ScenePrompts, SceneCharacter, SceneLocation,
    SceneGenerationRequest, ScenePromptRequest, SceneImageRequest, SceneVideoRequest
)
from app.models.story import StoryGraph
from app.models.character import CharacterBible
from app.models.provider import ProviderType
from app.providers.registry import ProviderRegistry
from app.services.project_manager import ProjectManager
from app.core.logging import get_project_logger, log_job_start, log_job_progress, log_job_complete, log_job_error, log_generation


class SceneService:
    """Service for scene management and cinematic generation."""
    
    def __init__(self, project_manager: ProjectManager, provider_registry: ProviderRegistry):
        self.project_manager = project_manager
        self.provider_registry = provider_registry
    
    async def generate_scenes(
        self,
        project_id: UUID,
        story_graph: StoryGraph,
        provider_name: str = "local_python",
        model_name: str = "llama-3-8b-instruct",
        job_id: Optional[str] = None
    ) -> List[Scene]:
        """Generate cinematic scenes from story graph."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        logger = get_project_logger(str(project_id), self.project_manager.project_root)
        
        if job_id:
            log_job_start(logger, job_id, "scene_generation")
        
        scenes = []
        scene_order = 0
        
        for act in story_graph.acts:
            for scene_id in act.scenes:
                scene_order += 1
                
                if job_id:
                    progress = int((scene_order / sum(len(a.scenes) for a in story_graph.acts)) * 100)
                    log_job_progress(logger, job_id, progress, f"generate_scene_{scene_id}")
                
                # Generate scene
                scene = await self._generate_scene(
                    project_id, scene_id, act.act_id, scene_order, story_graph,
                    provider_name, model_name
                )
                
                # Save scene
                self.project_manager.save_scene(project_dir, scene)
                scenes.append(scene)
        
        if job_id:
            log_job_progress(logger, job_id, 100, "save_scenes")
            log_job_complete(logger, job_id, "scene_generation", 0)
        
        return scenes
    
    async def _generate_scene(
        self,
        project_id: UUID,
        scene_id: str,
        act_id: str,
        order: int,
        story_graph: StoryGraph,
        provider_name: str,
        model_name: str
    ) -> Scene:
        """Generate a single cinematic scene."""
        provider = self.provider_registry.get_provider(
            ProviderType.LLM, provider_name, model_name
        )
        
        if not provider:
            await self.provider_registry.load_provider(
                ProviderType.LLM, provider_name, model_name
            )
            provider = self.provider_registry.get_provider(
                ProviderType.LLM, provider_name, model_name
            )
        
        if not provider or not provider.is_available():
            raise RuntimeError(f"LLM provider not available: {provider_name}:{model_name}")
        
        # Build scene generation prompt
        prompt = self._build_scene_prompt(scene_id, act_id, order, story_graph)
        
        # Generate structured scene data
        result = await provider.generate_structured(
            prompt=prompt,
            schema=self._get_scene_schema(),
            max_tokens=8192,
            temperature=0.4,
        )
        
        if not result.success:
            raise RuntimeError(f"Scene generation failed: {result.error}")
        
        # Parse result
        scene_data = result.data
        
        # Build Scene object
        scene = Scene(
            scene_id=scene_id,
            act_id=act_id,
            order=order,
            title=scene_data.get("title", f"Scene {order}"),
            duration_seconds=scene_data.get("duration_seconds", 10.0),
            source_segments=scene_data.get("source_segments", []),
            narration=scene_data.get("narration", ""),
            dialogue=scene_data.get("dialogue", []),
            characters=[
                SceneCharacter(**c) for c in scene_data.get("characters", [])
            ],
            location=SceneLocation(**scene_data.get("location", {})),
            action=scene_data.get("action", ""),
            emotion=scene_data.get("emotion", ""),
            camera=CameraConfig(**scene_data.get("camera", {})),
            lens=LensConfig(**scene_data.get("lens", {})),
            framing=scene_data.get("framing", ""),
            movement=scene_data.get("movement", ""),
            lighting=LightingConfig(**scene_data.get("lighting", {})),
            atmosphere=scene_data.get("atmosphere", ""),
            props=scene_data.get("props", []),
            environment=scene_data.get("environment", ""),
            visual_style=scene_data.get("visual_style", ""),
            music=MusicConfig(**scene_data.get("music", {})),
            sound_effects=[SFXConfig(**sfx) for sfx in scene_data.get("sound_effects", [])],
            created_by=f"{provider_name}:{model_name}",
            prompt_model=model_name,
        )
        
        return scene
    
    def _build_scene_prompt(self, scene_id: str, act_id: str, order: int, story_graph: StoryGraph) -> str:
        """Build prompt for scene generation."""
        # Find act
        act = story_graph.get_act(act_id)
        
        # Get characters in this act
        act_characters = []
        for char_id in act.characters if act else []:
            char = story_graph.get_character(char_id)
            if char:
                act_characters.append({
                    "id": char.character_id,
                    "name": char.canonical_name,
                    "role": char.role,
                    "description": char.description,
                })
        
        # Get location
        location = None
        for loc_id in act.locations if act else []:
            loc = story_graph.get_location(loc_id)
            if loc:
                location = {
                    "id": loc.location_id,
                    "name": loc.name,
                    "description": loc.description,
                    "type": loc.type,
                }
                break
        
        return f"""Generate a detailed cinematic scene breakdown for the following story segment.

SCENE ID: {scene_id}
ACT: {act_id} (Order: {order})
STORY: {story_graph.title}
STORY SUMMARY: {story_graph.summary}

ACT CONTEXT:
- Title: {act.title if act else 'Unknown'}
- Summary: {act.summary if act else 'Unknown'}

CHARACTERS IN ACT:
{json.dumps(act_characters, indent=2)}

LOCATION:
{json.dumps(location, indent=2) if location else 'Not specified'}

Create a cinematic scene with:
1. Title and duration
2. Narration text
3. Dialogue (with speaker, text, emotion)
4. Characters appearing (with screen time, emotion, action)
5. Location details (time of day, weather, atmosphere)
6. Action description
7. Dominant emotion
8. Camera setup (type, movement, speed, framing)
9. Lens specification (focal length, aperture, focus)
10. Lighting setup (type, key/fill/back, mood, color temperature)
11. Atmosphere and environment
12. Props
13. Visual style
14. Music (style, mood, instruments, tempo)
15. Sound effects (type, description, timing)

Return ONLY valid JSON matching the provided schema.
"""
    
    def _get_scene_schema(self) -> Dict[str, Any]:
        """Get JSON schema for scene."""
        return {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "duration_seconds": {"type": "number"},
                "source_segments": {"type": "array", "items": {"type": "string"}},
                "narration": {"type": "string"},
                "dialogue": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "speaker": {"type": "string"},
                            "text": {"type": "string"},
                            "emotion": {"type": "string"},
                        }
                    }
                },
                "characters": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "character_id": {"type": "string"},
                            "character_version": {"type": "string"},
                            "reference_image": {"type": "string"},
                            "canonical_description": {"type": "string"},
                            "screen_time_seconds": {"type": "number"},
                            "emotion": {"type": "string"},
                            "action": {"type": "string"},
                            "dialogue": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["character_id", "character_version"]
                    }
                },
                "location": {
                    "type": "object",
                    "properties": {
                        "location_id": {"type": "string"},
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "time_of_day": {"type": "string"},
                        "weather": {"type": "string"},
                        "atmosphere": {"type": "string"},
                        "environment": {"type": "string"},
                    },
                    "required": ["location_id", "name"]
                },
                "action": {"type": "string"},
                "emotion": {"type": "string"},
                "camera": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string"},
                        "movement": {"type": "string"},
                        "speed": {"type": "string"},
                        "start_frame": {"type": "string"},
                        "end_frame": {"type": "string"},
                        "focus_pulls": {"type": "array", "items": {"type": "object"}},
                    }
                },
                "lens": {
                    "type": "object",
                    "properties": {
                        "focal_length": {"type": "string"},
                        "aperture": {"type": "string"},
                        "focus": {"type": "string"},
                        "anamorphic": {"type": "boolean"},
                    }
                },
                "framing": {"type": "string"},
                "movement": {"type": "string"},
                "lighting": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string"},
                        "key_light": {"type": "string"},
                        "fill_light": {"type": "string"},
                        "back_light": {"type": "string"},
                        "practical_lights": {"type": "array", "items": {"type": "string"}},
                        "mood": {"type": "string"},
                        "color_temperature": {"type": "string"},
                        "time_of_day": {"type": "string"},
                    }
                },
                "atmosphere": {"type": "string"},
                "props": {"type": "array", "items": {"type": "string"}},
                "environment": {"type": "string"},
                "visual_style": {"type": "string"},
                "music": {
                    "type": "object",
                    "properties": {
                        "style": {"type": "string"},
                        "mood": {"type": "string"},
                        "instruments": {"type": "array", "items": {"type": "string"}},
                        "tempo": {"type": "string"},
                        "key": {"type": "string"},
                        "duration_seconds": {"type": "number"},
                        "loop": {"type": "boolean"},
                        "fade_in": {"type": "number"},
                        "fade_out": {"type": "number"},
                    }
                },
                "sound_effects": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string"},
                            "description": {"type": "string"},
                            "timing": {"type": "string"},
                            "timestamp": {"type": "number"},
                            "duration": {"type": "number"},
                            "volume": {"type": "number"},
                            "spatial": {"type": "string"},
                        }
                    }
                },
            },
            "required": ["title", "duration_seconds", "narration", "location", "action", "emotion"]
        }
    
    async def generate_scene_prompts(
        self,
        project_id: UUID,
        scene_id: str,
        provider_name: str = "local_python",
        model_name: str = "llama-3-8b-instruct",
    ) -> ScenePrompts:
        """Generate all cinematic prompts for a scene."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        scene = self.project_manager.load_scene(project_dir, scene_id)
        
        if not scene:
            raise ValueError(f"Scene not found: {scene_id}")
        
        provider = self.provider_registry.get_provider(
            ProviderType.LLM, provider_name, model_name
        )
        
        if not provider:
            await self.provider_registry.load_provider(
                ProviderType.LLM, provider_name, model_name
            )
            provider = self.provider_registry.get_provider(
                ProviderType.LLM, provider_name, model_name
            )
        
        # Build comprehensive prompt engineering prompt
        prompt = self._build_prompt_engineering_prompt(scene)
        
        result = await provider.generate_structured(
            prompt=prompt,
            schema=self._get_prompts_schema(),
            max_tokens=8192,
            temperature=0.3,
        )
        
        if not result.success:
            raise RuntimeError(f"Prompt generation failed: {result.error}")
        
        prompts_data = result.data
        prompts = ScenePrompts(**prompts_data)
        
        # Save prompts to scene
        scene.prompts = prompts
        self.project_manager.save_scene(project_dir, scene)
        
        # Save individual prompt files
        prompt_dir = project_dir / "prompts" / "scenes"
        prompt_dir.mkdir(parents=True, exist_ok=True)
        
        for field_name, prompt_text in prompts.model_dump().items():
            if prompt_text:
                version = self.project_manager.get_next_version(
                    project_dir, f"{scene_id}_{field_name}", "prompts/scenes"
                )
                (prompt_dir / f"{scene_id}_{field_name}_{version}.txt").write_text(prompt_text, encoding="utf-8")
        
        return prompts
    
    def _build_prompt_engineering_prompt(self, scene: Scene) -> str:
        """Build prompt for cinematic prompt engineering."""
        # Get character descriptions
        char_descriptions = []
        for sc in scene.characters:
            char_descriptions.append(f"- {sc.character_id}: {sc.canonical_description}")
        
        return f"""Generate comprehensive cinematic prompts for the following scene.

SCENE: {scene.scene_id} - {scene.title}
DURATION: {scene.duration_seconds}s
NARRATION: {scene.narration}
ACTION: {scene.action}
EMOTION: {scene.emotion}

CHARACTERS:
{chr(10).join(char_descriptions) if char_descriptions else 'None'}

LOCATION: {scene.location.name}
LOCATION DESCRIPTION: {scene.location.description}
TIME OF DAY: {scene.location.time_of_day}
WEATHER: {scene.location.weather}
ATMOSPHERE: {scene.atmosphere}

CAMERA: {scene.camera.type}, {scene.camera.movement}, {scene.camera.speed}
LENS: {scene.lens.focal_length}, {scene.lens.aperture}
LIGHTING: {scene.lighting.type}, {scene.lighting.mood}
VISUAL STYLE: {scene.visual_style}

MUSIC: {scene.music.style}, {scene.music.mood}, {', '.join(scene.music.instruments)}
SOUND EFFECTS: {len(scene.sound_effects)} effects

Generate the following detailed prompts:
1. MASTER PROMPT - Complete scene description for image generation
2. CHARACTER PROMPT - Character-focused prompt with all characters
3. ENVIRONMENT PROMPT - Location/environment only
4. CAMERA PROMPT - Camera movement and framing details
5. LENS PROMPT - Lens characteristics and depth of field
6. LIGHTING PROMPT - Lighting setup and mood
7. COMPOSITION PROMPT - Composition rules and framing
8. MOTION PROMPT - Movement and animation details
9. IMAGE PROMPT - Optimized for text-to-image generation
10. I2V PROMPT - Optimized for image-to-video generation
11. VOICE PROMPT - Voice characteristics for TTS
12. MUSIC PROMPT - Detailed music generation prompt
13. SFX PROMPT - Detailed sound effects prompt
14. NEGATIVE PROMPT - What to avoid

Each prompt should be detailed, production-ready, and specific.
Return ONLY valid JSON matching the provided schema.
"""
    
    def _get_prompts_schema(self) -> Dict[str, Any]:
        """Get JSON schema for scene prompts."""
        return {
            "type": "object",
            "properties": {
                "master": {"type": "string"},
                "character": {"type": "string"},
                "environment": {"type": "string"},
                "camera": {"type": "string"},
                "lens": {"type": "string"},
                "lighting": {"type": "string"},
                "composition": {"type": "string"},
                "motion": {"type": "string"},
                "image": {"type": "string"},
                "i2v": {"type": "string"},
                "voice": {"type": "string"},
                "music": {"type": "string"},
                "sfx": {"type": "string"},
                "negative": {"type": "string"},
            },
            "required": ["master", "character", "environment", "camera", "lens", "lighting", "composition", "motion", "image", "i2v", "voice", "music", "sfx", "negative"]
        }
    
    async def generate_scene_image(
        self,
        project_id: UUID,
        request: SceneImageRequest,
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate scene keyframe image."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        logger = get_project_logger(str(project_id), self.project_manager.project_root)
        
        if job_id:
            log_job_start(logger, job_id, "scene_image_generation")
        
        scene = self.project_manager.load_scene(project_dir, request.scene_id)
        if not scene:
            raise ValueError(f"Scene not found: {request.scene_id}")
        
        provider = self.provider_registry.get_provider(
            ProviderType.IMAGE_GENERATION, "local_python", "sdxl-base"
        )
        
        if not provider:
            await self.provider_registry.load_provider(
                ProviderType.IMAGE_GENERATION, "local_python", "sdxl-base"
            )
            provider = self.provider_registry.get_provider(
                ProviderType.IMAGE_GENERATION, "local_python", "sdxl-base"
            )
        
        if not provider or not provider.is_available():
            raise RuntimeError("Image generation provider not available")
        
        if job_id:
            log_job_progress(logger, job_id, 25, "load_image_model")
        
        # Use scene's image prompt or master prompt
        prompt = request.prompt or scene.prompts.image or scene.prompts.master
        negative = request.negative_prompt or scene.prompts.negative
        
        result = await provider.generate(
            prompt=prompt,
            negative_prompt=negative,
            width=request.width,
            height=request.height,
            seed=request.seed,
        )
        
        if job_id:
            log_job_progress(logger, job_id, 75, "save_image")
        
        if not result.success:
            raise RuntimeError(f"Image generation failed: {result.error}")
        
        # Save image
        image_data = result.data
        image = image_data["image"]
        
        version = self.project_manager.get_next_version(
            project_dir, f"{request.scene_id}", "images/scenes"
        )
        
        image_filename = f"{request.scene_id}_{version}.png"
        image_path = project_dir / "images" / "scenes" / image_filename
        image_path.parent.mkdir(parents=True, exist_ok=True)
        
        image.save(image_path)
        
        # Update scene
        scene.images.append(f"images/scenes/{image_filename}")
        self.project_manager.save_scene(project_dir, scene)
        
        # Save metadata
        from app.models.asset import AssetMetadata, AssetType
        asset = AssetMetadata(
            asset_type=AssetType.SCENE_IMAGE,
            file_path=f"images/scenes/{image_filename}",
            version=version,
            project_id=project_id,
            generator="local_python:sdxl-base",
            generation_params={
                "width": image_data["width"],
                "height": image_data["height"],
                "seed": image_data["seed"],
                "steps": image_data.get("steps"),
                "guidance_scale": image_data.get("guidance_scale"),
            },
            prompt=prompt,
            negative_prompt=negative,
            seed=image_data["seed"],
            file_size_bytes=image_path.stat().st_size,
            sha256=self.project_manager.compute_file_hash(image_path),
            dimensions={"width": image_data["width"], "height": image_data["height"]},
        )
        self.project_manager.save_asset_metadata(project_dir, asset)
        
        if job_id:
            log_job_progress(logger, job_id, 100, "complete")
            log_job_complete(logger, job_id, "scene_image_generation", 0)
        
        log_generation(
            logger,
            "scene_image",
            "local_python:diffusers",
            "sdxl-base",
            0,
            scene_id=request.scene_id,
            version=version,
        )
        
        return {
            "image_path": f"images/scenes/{image_filename}",
            "version": version,
            "metadata": image_data,
        }
    
    async def generate_scene_video(
        self,
        project_id: UUID,
        request: SceneVideoRequest,
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate scene video from image."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        logger = get_project_logger(str(project_id), self.project_manager.project_root)
        
        if job_id:
            log_job_start(logger, job_id, "scene_video_generation")
        
        scene = self.project_manager.load_scene(project_dir, request.scene_id)
        if not scene:
            raise ValueError(f"Scene not found: {request.scene_id}")
        
        provider = self.provider_registry.get_provider(
            ProviderType.VIDEO_GENERATION, "local_python", "svd-xt"
        )
        
        if not provider:
            await self.provider_registry.load_provider(
                ProviderType.VIDEO_GENERATION, "local_python", "svd-xt"
            )
            provider = self.provider_registry.get_provider(
                ProviderType.VIDEO_GENERATION, "local_python", "svd-xt"
            )
        
        if not provider or not provider.is_available():
            raise RuntimeError("Video generation provider not available")
        
        if job_id:
            log_job_progress(logger, job_id, 25, "load_video_model")
        
        # Use scene's i2v prompt
        prompt = request.prompt or scene.prompts.i2v
        negative = request.negative_prompt or scene.prompts.negative
        
        result = await provider.generate(
            image_path=request.image_path,
            prompt=prompt,
            negative_prompt=negative,
            num_frames=request.num_frames,
            fps=request.fps,
        )
        
        if job_id:
            log_job_progress(logger, job_id, 75, "save_video")
        
        if not result.success:
            raise RuntimeError(f"Video generation failed: {result.error}")
        
        # Save video
        video_data = result.data
        video_path = video_data["video_path"]
        
        version = self.project_manager.get_next_version(
            project_dir, f"{request.scene_id}", "video/scenes"
        )
        
        video_filename = f"{request.scene_id}_{version}.mp4"
        dest_path = project_dir / "video" / "scenes" / video_filename
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        import shutil
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
            generator="local_python:svd-xt",
            generation_params={
                "num_frames": video_data["num_frames"],
                "fps": video_data["fps"],
                "duration_seconds": video_data["duration_seconds"],
            },
            prompt=prompt,
            negative_prompt=negative,
            file_size_bytes=dest_path.stat().st_size,
            sha256=self.project_manager.compute_file_hash(dest_path),
            duration_seconds=video_data["duration_seconds"],
        )
        self.project_manager.save_asset_metadata(project_dir, asset)
        
        if job_id:
            log_job_progress(logger, job_id, 100, "complete")
            log_job_complete(logger, job_id, "scene_video_generation", 0)
        
        log_generation(
            logger,
            "scene_video",
            "local_python:diffusers",
            "svd-xt",
            0,
            scene_id=request.scene_id,
            version=version,
        )
        
        return {
            "video_path": f"video/scenes/{video_filename}",
            "version": version,
            "metadata": video_data,
        }
    
    def get_scene(self, project_id: UUID, scene_id: str) -> Optional[Scene]:
        """Get scene by ID."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        return self.project_manager.load_scene(project_dir, scene_id)
    
    def list_scenes(self, project_id: UUID) -> List[Dict[str, Any]]:
        """List all scenes for a project."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        return self.project_manager.load_scenes_index(project_dir)
    
    async def generate_silent_master(
        self,
        project_id: UUID,
        job_id: Optional[str] = None
    ) -> str:
        """Generate silent master video by concatenating all scene videos."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        logger = get_project_logger(str(project_id), self.project_manager.project_root)
        
        if job_id:
            log_job_start(logger, job_id, "silent_master_generation")
        
        scenes = self.list_scenes(project_id)
        scene_videos = []
        
        for scene_info in scenes:
            scene = self.get_scene(project_id, scene_info["scene_id"])
            if scene and scene.video_path:
                video_path = project_dir / scene.video_path
                if video_path.exists():
                    scene_videos.append(str(video_path))
        
        if not scene_videos:
            raise ValueError("No scene videos found to create silent master")
        
        if job_id:
            log_job_progress(logger, job_id, 50, "concatenate_videos")
        
        # Use FFmpeg to concatenate
        from app.utils.ffmpeg import FFmpegWrapper
        ffmpeg = FFmpegWrapper(self.project_manager._settings.ffmpeg_path)
        
        version = self.project_manager.get_next_version(
            project_dir, "master", "video/silent_master"
        )
        
        output_path = project_dir / "video" / "silent_master" / f"master_{version}.mp4"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        await ffmpeg.concat_videos(scene_videos, str(output_path))
        
        if job_id:
            log_job_progress(logger, job_id, 100, "complete")
            log_job_complete(logger, job_id, "silent_master_generation", 0)
        
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
        
        # Get latest version
        latest = max(masters, key=lambda f: f.stem)
        return f"video/silent_master/{latest.name}"