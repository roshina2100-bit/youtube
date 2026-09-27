"""
Prompt Engine for the Cinematic Video Studio.
Generates detailed cinematic prompts for all generation tasks.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.models.scene import Scene, ScenePrompts
from app.models.character import CharacterBible
from app.models.story import StoryGraph
from app.models.provider import ProviderType
from app.providers.registry import ProviderRegistry
from app.services.project_manager import ProjectManager


class PromptEngine:
    """Engine for generating detailed cinematic prompts."""
    
    def __init__(self, project_manager: ProjectManager, provider_registry: ProviderRegistry):
        self.project_manager = project_manager
        self.provider_registry = provider_registry
    
    def build_master_prompt(self, scene: Scene, story_graph: StoryGraph) -> str:
        """Build master cinematic prompt for a scene."""
        parts = []
        
        # Subject
        if scene.characters:
            char_names = [sc.canonical_description.split('.')[0] for sc in scene.characters[:3]]
            parts.append(f"Subject: {', '.join(char_names)}")
        
        # Environment
        parts.append(f"Environment: {scene.location.description}")
        parts.append(f"Setting: {scene.environment}")
        parts.append(f"Time: {scene.location.time_of_day}")
        parts.append(f"Weather: {scene.location.weather}")
        parts.append(f"Atmosphere: {scene.atmosphere}")
        
        # Camera
        parts.append(f"Camera: {scene.camera.type}, {scene.camera.movement}, {scene.camera.speed}")
        parts.append(f"Framing: {scene.framing}")
        
        # Lens
        parts.append(f"Lens: {scene.lens.focal_length}, {scene.lens.aperture}, {scene.lens.focus}")
        
        # Lighting
        parts.append(f"Lighting: {scene.lighting.type}, {scene.lighting.key_light}, {scene.lighting.mood}")
        parts.append(f"Color Temperature: {scene.lighting.color_temperature}")
        
        # Composition
        parts.append(f"Composition: {scene.composition}")
        
        # Motion
        parts.append(f"Motion: {scene.movement}")
        
        # Visual Style
        parts.append(f"Style: {scene.visual_style}")
        
        # Quality modifiers
        parts.append("8k resolution, masterpiece, highly detailed, cinematic, photorealistic")
        
        return " | ".join(parts)
    
    def build_character_prompt(self, scene: Scene, character: CharacterBible) -> str:
        """Build character-specific prompt."""
        parts = [
            f"Character: {character.canonical_name}",
            f"Appearance: {character.visual_identity}",
            f"Face: {character.physical_appearance.face}",
            f"Hair: {character.physical_appearance.hair}",
            f"Skin: {character.physical_appearance.skin}",
            f"Body: {character.physical_appearance.body}",
            f"Clothing: {character.clothing.upper}, {character.clothing.lower}",
            f"Accessories: {', '.join(character.clothing.accessories + character.clothing.jewelry)}",
        ]
        
        if character.clothing.headwear:
            parts.append(f"Headwear: {character.clothing.headwear}")
        
        parts.append("Cinematic portrait, sharp focus, detailed texture, professional lighting")
        
        return " | ".join(parts)
    
    def build_environment_prompt(self, scene: Scene) -> str:
        """Build environment-only prompt."""
        parts = [
            f"Location: {scene.location.name}",
            f"Description: {scene.location.description}",
            f"Environment: {scene.environment}",
            f"Time of day: {scene.location.time_of_day}",
            f"Weather: {scene.location.weather}",
            f"Atmosphere: {scene.atmosphere}",
            f"Props: {', '.join(scene.props)}",
        ]
        
        parts.append("Wide establishing shot, environmental storytelling, atmospheric perspective")
        
        return " | ".join(parts)
    
    def build_camera_prompt(self, scene: Scene) -> str:
        """Build camera-specific prompt."""
        parts = [
            f"Camera type: {scene.camera.type}",
            f"Movement: {scene.camera.movement}",
            f"Speed: {scene.camera.speed}",
            f"Start frame: {scene.camera.start_frame}",
            f"End frame: {scene.camera.end_frame}",
        ]
        
        if scene.camera.focus_pulls:
            parts.append(f"Focus pulls: {len(scene.camera.focus_pulls)} planned")
        
        return " | ".join(parts)
    
    def build_lens_prompt(self, scene: Scene) -> str:
        """Build lens-specific prompt."""
        parts = [
            f"Focal length: {scene.lens.focal_length}",
            f"Aperture: {scene.lens.aperture}",
            f"Focus: {scene.lens.focus}",
        ]
        
        if scene.lens.anamorphic:
            parts.append("Anamorphic: true")
        
        parts.append("Cinematic lens characteristics, optical imperfections, lens flare")
        
        return " | ".join(parts)
    
    def build_lighting_prompt(self, scene: Scene) -> str:
        """Build lighting-specific prompt."""
        parts = [
            f"Lighting type: {scene.lighting.type}",
            f"Key light: {scene.lighting.key_light}",
            f"Fill light: {scene.lighting.fill_light}",
            f"Back light: {scene.lighting.back_light}",
            f"Mood: {scene.lighting.mood}",
            f"Color temperature: {scene.lighting.color_temperature}",
            f"Time of day: {scene.lighting.time_of_day}",
        ]
        
        if scene.lighting.practical_lights:
            parts.append(f"Practical lights: {', '.join(scene.lighting.practical_lights)}")
        
        parts.append("Volumetric lighting, cinematic contrast, motivated lighting")
        
        return " | ".join(parts)
    
    def build_composition_prompt(self, scene: Scene) -> str:
        """Build composition-specific prompt."""
        parts = [
            f"Framing: {scene.framing}",
            f"Rule of thirds applied",
            f"Depth layers: foreground, midground, background",
            f"Leading lines: environmental",
        ]
        
        return " | ".join(parts)
    
    def build_motion_prompt(self, scene: Scene) -> str:
        """Build motion/animation prompt."""
        parts = [
            f"Camera movement: {scene.camera.movement} at {scene.camera.speed} speed",
            f"Subject motion: {scene.movement}",
            f"Duration: {scene.duration_seconds} seconds",
        ]
        
        if scene.sound_effects:
            parts.append(f"Audio cues: {len(scene.sound_effects)} sound effects synchronized")
        
        return " | ".join(parts)
    
    def build_image_prompt(self, scene: Scene) -> str:
        """Build optimized text-to-image prompt."""
        master = self.build_master_prompt(scene, None)
        return f"{master}, best quality, ultra high res, 8k, masterpiece"
    
    def build_i2v_prompt(self, scene: Scene) -> str:
        """Build optimized image-to-video prompt."""
        parts = [
            f"Camera: {scene.camera.type} {scene.camera.movement} {scene.camera.speed}",
            f"Subject motion: {scene.movement}",
            f"Duration: {scene.duration_seconds}s at {scene.duration_seconds/25:.1f}fps",
            f"Atmosphere: {scene.atmosphere}",
        ]
        
        return " | ".join(parts)
    
    def build_voice_prompt(self, scene: Scene, character: Optional[CharacterBible] = None) -> str:
        """Build voice/TTS prompt."""
        if character:
            return f"Voice for {character.canonical_name}: {character.personality.traits}, {character.personality.emotions}, {scene.emotion} tone"
        
        return f"Narrator voice: {scene.emotion} tone, cinematic, storytelling style, measured pace"
    
    def build_music_prompt(self, scene: Scene) -> str:
        """Build music generation prompt."""
        parts = [
            f"Style: {scene.music.style}",
            f"Mood: {scene.music.mood}",
            f"Instruments: {', '.join(scene.music.instruments)}",
            f"Tempo: {scene.music.tempo}",
            f"Duration: {scene.music.duration_seconds}s",
        ]
        
        if scene.music.key:
            parts.append(f"Key: {scene.music.key}")
        
        parts.append("Cinematic score, emotional resonance, professional production")
        
        return " | ".join(parts)
    
    def build_sfx_prompt(self, scene: Scene) -> str:
        """Build sound effects prompt."""
        if not scene.sound_effects:
            return "Ambient silence, subtle room tone"
        
        parts = []
        for sfx in scene.sound_effects:
            parts.append(f"{sfx.type}: {sfx.description} at {sfx.timing}")
        
        return " | ".join(parts)
    
    def build_negative_prompt(self, scene: Scene, character: Optional[CharacterBible] = None) -> str:
        """Build comprehensive negative prompt."""
        base_negatives = [
            "ugly, deformed, noisy, blurry, low quality, distortion",
            "bad anatomy, extra limbs, missing limbs, floating limbs",
            "disconnected limbs, mutation, mutated, ugly, disgusting",
            "poorly drawn face, poorly drawn hands, poorly drawn feet",
            "mutation, deformed, blurry, bad anatomy, bad proportions",
            "extra arms, extra legs, extra fingers, extra toes",
            "cartoon, anime, sketch, drawing, illustration, painting",
            "watermark, text, signature, logo, username, artist name",
            "lowres, bad anatomy, bad hands, normal quality",
            "worst quality, low quality, normal quality, jpeg artifacts",
        ]
        
        if character and character.negative_prompt:
            base_negatives.append(character.negative_prompt)
        
        if scene.prompts.negative:
            base_negatives.append(scene.prompts.negative)
        
        return ", ".join(base_negatives)
    
    async def generate_all_prompts(
        self,
        project_id: UUID,
        scene_id: str,
        provider_name: str = "local_python",
        model_name: str = "llama-3-8b-instruct",
    ) -> ScenePrompts:
        """Generate all prompts for a scene using LLM."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        scene = self.project_manager.load_scene(project_dir, scene_id)
        
        if not scene:
            raise ValueError(f"Scene not found: {scene_id}")
        
        # Load story for context
        story = self.project_manager.load_story(project_dir)
        
        # Build prompts using templates (fast, no LLM needed)
        prompts = ScenePrompts(
            master=self.build_master_prompt(scene, story),
            character=self.build_character_prompt(scene, None),  # Would need character
            environment=self.build_environment_prompt(scene),
            camera=self.build_camera_prompt(scene),
            lens=self.build_lens_prompt(scene),
            lighting=self.build_lighting_prompt(scene),
            composition=self.build_composition_prompt(scene),
            motion=self.build_motion_prompt(scene),
            image=self.build_image_prompt(scene),
            i2v=self.build_i2v_prompt(scene),
            voice=self.build_voice_prompt(scene),
            music=self.build_music_prompt(scene),
            sfx=self.build_sfx_prompt(scene),
            negative=self.build_negative_prompt(scene),
        )
        
        # Save to scene
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
    
    def get_prompt_templates(self) -> Dict[str, str]:
        """Get all prompt templates."""
        return {
            "master": "Subject: {subject} | Environment: {environment} | Camera: {camera} | Lens: {lens} | Lighting: {lighting} | Composition: {composition} | Motion: {motion} | Style: {style} | Quality: 8k, masterpiece, highly detailed, cinematic",
            "character": "Character: {name} | Appearance: {appearance} | Clothing: {clothing} | Accessories: {accessories} | Expression: {expression} | Lighting: {lighting} | Cinematic portrait, sharp focus, detailed texture",
            "environment": "Location: {location} | Description: {description} | Time: {time} | Weather: {weather} | Atmosphere: {atmosphere} | Props: {props} | Wide establishing shot, environmental storytelling",
            "camera": "Camera: {type} | Movement: {movement} | Speed: {speed} | Start: {start_frame} | End: {end_frame} | Framing: {framing}",
            "lens": "Focal length: {focal_length} | Aperture: {aperture} | Focus: {focus} | Anamorphic: {anamorphic} | Cinematic lens characteristics",
            "lighting": "Type: {type} | Key: {key_light} | Fill: {fill_light} | Back: {back_light} | Mood: {mood} | Temperature: {color_temperature} | Time: {time_of_day} | Volumetric, cinematic contrast",
            "composition": "Framing: {framing} | Rule of thirds | Depth layers | Leading lines | Visual balance",
            "motion": "Camera: {camera_movement} | Subject: {subject_motion} | Duration: {duration}s | Audio sync: {audio_cues}",
            "image": "{master_prompt} | Best quality, ultra high res, 8k, masterpiece",
            "i2v": "Camera: {camera_movement} | Subject motion: {subject_motion} | Duration: {duration}s | Atmosphere: {atmosphere} | Smooth, cinematic motion",
            "voice": "Voice: {character_voice} | Tone: {tone} | Pace: {pace} | Emotion: {emotion} | Language: {language}",
            "music": "Style: {style} | Mood: {mood} | Instruments: {instruments} | Tempo: {tempo} | Duration: {duration}s | Key: {key} | Cinematic score",
            "sfx": "{sfx_list} | Spatial: {spatial} | Volume: {volume} | Timing: {timing}",
            "negative": "ugly, deformed, noisy, blurry, low quality, distortion, bad anatomy, extra limbs, missing limbs, floating limbs, disconnected limbs, mutation, mutated, poorly drawn face, poorly drawn hands, poorly drawn feet, cartoon, anime, sketch, drawing, illustration, painting, watermark, text, signature, logo, username, artist name, lowres, worst quality, jpeg artifacts",
        }