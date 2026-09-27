"""
Character Service for the Cinematic Video Studio.
Handles character extraction, character bible creation, image generation, and approval workflow.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.models.character import (
    CharacterBible, CharacterStatus, CharacterVersion,
    PhysicalAppearance, Clothing, Personality, ContinuityRules,
    CharacterPromptRequest, CharacterImageRequest, CharacterApprovalRequest
)
from app.models.story import StoryGraph, CharacterRef
from app.models.provider import ProviderType
from app.providers.registry import ProviderRegistry
from app.services.project_manager import ProjectManager
from app.core.logging import get_project_logger, log_job_start, log_job_progress, log_job_complete, log_job_error, log_generation


class CharacterService:
    """Service for character management and image generation."""
    
    def __init__(self, project_manager: ProjectManager, provider_registry: ProviderRegistry):
        self.project_manager = project_manager
        self.provider_registry = provider_registry
    
    async def extract_characters(
        self, 
        project_id: UUID, 
        story_graph: StoryGraph,
        provider_name: str = "local_python",
        model_name: str = "llama-3-8b-instruct",
        job_id: Optional[str] = None
    ) -> List[CharacterBible]:
        """Extract detailed character bibles from story graph."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        logger = get_project_logger(str(project_id), self.project_manager.project_root)
        
        if job_id:
            log_job_start(logger, job_id, "character_extraction")
        
        characters = []
        
        for i, char_ref in enumerate(story_graph.characters):
            if job_id:
                progress = int((i / len(story_graph.characters)) * 100)
                log_job_progress(logger, job_id, progress, f"extract_character_{char_ref.character_id}")
            
            # Generate detailed character bible
            character = await self._generate_character_bible(
                project_id, char_ref, story_graph, provider_name, model_name
            )
            
            # Save character
            self.project_manager.save_character(project_dir, character)
            characters.append(character)
        
        if job_id:
            log_job_progress(logger, job_id, 100, "save_characters")
            log_job_complete(logger, job_id, "character_extraction", 0)
        
        return characters
    
    async def _generate_character_bible(
        self,
        project_id: UUID,
        char_ref: CharacterRef,
        story_graph: StoryGraph,
        provider_name: str,
        model_name: str
    ) -> CharacterBible:
        """Generate detailed character bible using LLM."""
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
        
        # Build character analysis prompt
        prompt = self._build_character_prompt(char_ref, story_graph)
        
        # Generate structured character data
        result = await provider.generate_structured(
            prompt=prompt,
            schema=self._get_character_schema(),
            max_tokens=4096,
            temperature=0.5,
        )
        
        if not result.success:
            raise RuntimeError(f"Character generation failed: {result.error}")
        
        # Parse result
        char_data = result.data
        
        # Build CharacterBible
        character = CharacterBible(
            character_id=char_ref.character_id,
            canonical_name=char_ref.canonical_name,
            aliases=char_ref.aliases,
            role=char_ref.role,
            importance=char_ref.importance,
            physical_appearance=PhysicalAppearance(**char_data.get("physical_appearance", {})),
            clothing=Clothing(**char_data.get("clothing", {})),
            personality=Personality(**char_data.get("personality", {})),
            relationships=char_data.get("relationships", []),
            story_role=char_data.get("story_role", char_ref.description),
            character_arc=char_data.get("character_arc", ""),
            visual_identity=char_data.get("visual_identity", ""),
            negative_prompt=char_data.get("negative_prompt", ""),
            continuity_rules=ContinuityRules(**char_data.get("continuity_rules", {})),
            prompt_template=char_data.get("prompt_template", ""),
            status=CharacterStatus.DRAFT,
            created_by=f"{provider_name}:{model_name}",
        )
        
        return character
    
    def _build_character_prompt(self, char_ref: CharacterRef, story_graph: StoryGraph) -> str:
        """Build prompt for character bible generation."""
        # Find character's scenes
        char_scenes = []
        for act in story_graph.acts:
            for scene_id in act.scenes:
                # Would need to check if character appears in scene
                pass
        
        # Find relationships
        relationships = []
        for rel in story_graph.relationships:
            if rel.character_id == char_ref.character_id:
                related_char = story_graph.get_character(rel.related_character_id)
                if related_char:
                    relationships.append({
                        "character": related_char.canonical_name,
                        "type": rel.type,
                        "description": rel.description,
                    })
        
        return f"""Create a detailed character bible for the following character from the story.

CHARACTER REFERENCE:
- Name: {char_ref.canonical_name}
- Aliases: {', '.join(char_ref.aliases) if char_ref.aliases else 'None'}
- Role: {char_ref.role}
- Importance: {char_ref.importance}
- Description: {char_ref.description}

STORY CONTEXT:
- Title: {story_graph.title}
- Summary: {story_graph.summary}

RELATIONSHIPS:
{json.dumps(relationships, indent=2) if relationships else 'None specified'}

Create a comprehensive character bible with:
1. Physical appearance (face, hair, skin, body, eyes, distinguishing features)
2. Clothing and accessories (upper, lower, footwear, outerwear, accessories, jewelry, headwear, props)
3. Personality (traits, emotions, motivations, fears, quirks)
4. Story role and character arc
5. Visual identity description for image generation
6. Negative prompt for image generation (what to avoid)
7. Continuity rules (locked features, variable features, forbidden changes)
8. Prompt template for consistent image generation

Return ONLY valid JSON matching the provided schema.
"""
    
    def _get_character_schema(self) -> Dict[str, Any]:
        """Get JSON schema for character bible."""
        return {
            "type": "object",
            "properties": {
                "physical_appearance": {
                    "type": "object",
                    "properties": {
                        "face": {"type": "string"},
                        "hair": {"type": "string"},
                        "skin": {"type": "string"},
                        "body": {"type": "string"},
                        "eyes": {"type": "string"},
                        "distinguishing_features": {"type": "array", "items": {"type": "string"}},
                    }
                },
                "clothing": {
                    "type": "object",
                    "properties": {
                        "upper": {"type": "string"},
                        "lower": {"type": "string"},
                        "footwear": {"type": "string"},
                        "outerwear": {"type": "string"},
                        "accessories": {"type": "array", "items": {"type": "string"}},
                        "jewelry": {"type": "array", "items": {"type": "string"}},
                        "headwear": {"type": "string"},
                        "props": {"type": "array", "items": {"type": "string"}},
                    }
                },
                "personality": {
                    "type": "object",
                    "properties": {
                        "traits": {"type": "array", "items": {"type": "string"}},
                        "emotions": {"type": "array", "items": {"type": "string"}},
                        "motivations": {"type": "array", "items": {"type": "string"}},
                        "fears": {"type": "array", "items": {"type": "string"}},
                        "quirks": {"type": "array", "items": {"type": "string"}},
                    }
                },
                "relationships": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "character": {"type": "string"},
                            "type": {"type": "string"},
                            "description": {"type": "string"},
                        }
                    }
                },
                "story_role": {"type": "string"},
                "character_arc": {"type": "string"},
                "visual_identity": {"type": "string"},
                "negative_prompt": {"type": "string"},
                "continuity_rules": {
                    "type": "object",
                    "properties": {
                        "locked_features": {"type": "array", "items": {"type": "string"}},
                        "variable_features": {"type": "array", "items": {"type": "string"}},
                        "forbidden_changes": {"type": "array", "items": {"type": "string"}},
                    }
                },
                "prompt_template": {"type": "string"},
            },
            "required": ["physical_appearance", "clothing", "personality", "visual_identity", "negative_prompt", "continuity_rules", "prompt_template"]
        }
    
    async def generate_character_prompt(
        self,
        project_id: UUID,
        character_id: str,
        provider_name: str = "local_python",
        model_name: str = "llama-3-8b-instruct",
    ) -> CharacterVersion:
        """Generate character image prompt."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        character = self.project_manager.load_character(project_dir, character_id)
        
        if not character:
            raise ValueError(f"Character not found: {character_id}")
        
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
        
        # Build prompt using template
        prompt = character.prompt_template.format(
            canonical_name=character.canonical_name,
            physical_appearance=character.physical_appearance.model_dump(),
            clothing=character.clothing.model_dump(),
            visual_identity=character.visual_identity,
            lighting="cinematic lighting, volumetric, golden hour",
            camera="35mm lens, f/1.8, shallow depth of field",
            lens="35mm",
            composition="rule of thirds, centered subject",
            atmosphere="epic, cinematic, detailed",
        )
        
        # Generate with LLM to refine
        refine_prompt = f"""Refine this character image prompt for maximum quality and consistency:

BASE PROMPT: {prompt}

CHARACTER: {character.canonical_name}
VISUAL IDENTITY: {character.visual_identity}
NEGATIVE PROMPT: {character.negative_prompt}

Create an optimized, detailed prompt for cinematic character portrait generation.
Return ONLY the refined prompt text, no explanations.
"""
        
        result = await provider.generate(
            prompt=refine_prompt,
            max_tokens=1024,
            temperature=0.3,
        )
        
        refined_prompt = result.data if result.success else prompt
        
        # Create version
        version = self.project_manager.get_next_version(
            project_dir, f"{character_id}_prompt", "prompts/characters"
        )
        
        char_version = CharacterVersion(
            version=version,
            prompt=refined_prompt,
            negative_prompt=character.negative_prompt,
            created_by=f"{provider_name}:{model_name}",
        )
        
        character.add_version(char_version)
        self.project_manager.save_character(project_dir, character)
        
        # Save prompt files
        prompt_dir = project_dir / "prompts" / "characters"
        prompt_dir.mkdir(parents=True, exist_ok=True)
        
        (prompt_dir / f"{character_id}_prompt_{version}.txt").write_text(refined_prompt, encoding="utf-8")
        (prompt_dir / f"{character_id}_negative_{version}.txt").write_text(character.negative_prompt, encoding="utf-8")
        
        return char_version
    
    async def generate_character_image(
        self,
        project_id: UUID,
        request: CharacterImageRequest,
        job_id: Optional[str] = None
    ) -> CharacterVersion:
        """Generate character image."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        logger = get_project_logger(str(project_id), self.project_manager.project_root)
        
        if job_id:
            log_job_start(logger, job_id, "character_image_generation")
        
        character = self.project_manager.load_character(project_dir, request.character_id)
        if not character:
            raise ValueError(f"Character not found: {request.character_id}")
        
        # Get version data
        version_data = character.versions.get(request.version)
        if not version_data:
            raise ValueError(f"Version not found: {request.version}")
        
        # Get image provider
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
        
        # Generate image
        result = await provider.generate(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt,
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
        image = image_data["image"]  # PIL Image
        
        # Determine version
        version = self.project_manager.get_next_version(
            project_dir, f"{request.character_id}", "images/characters"
        )
        
        image_filename = f"{request.character_id}_{version}.png"
        image_path = project_dir / "images" / "characters" / image_filename
        image_path.parent.mkdir(parents=True, exist_ok=True)
        
        image.save(image_path)
        
        # Update version with image info
        version_data.image_path = f"images/characters/{image_filename}"
        version_data.image_metadata = {
            "width": image_data["width"],
            "height": image_data["height"],
            "seed": image_data["seed"],
            "steps": image_data.get("steps"),
            "guidance_scale": image_data.get("guidance_scale"),
            "model": "sdxl-base",
        }
        
        character.add_version(version_data)
        character.status = CharacterStatus.GENERATED
        self.project_manager.save_character(project_dir, character)
        
        # Save metadata
        from app.models.asset import AssetMetadata, AssetType
        asset = AssetMetadata(
            asset_type=AssetType.CHARACTER_IMAGE,
            file_path=f"images/characters/{image_filename}",
            version=version,
            project_id=project_id,
            generator="local_python:sdxl-base",
            generation_params=version_data.image_metadata,
            prompt=request.prompt,
            negative_prompt=request.negative_prompt,
            seed=image_data["seed"],
            file_size_bytes=image_path.stat().st_size,
            sha256=self.project_manager.compute_file_hash(image_path),
            dimensions={"width": image_data["width"], "height": image_data["height"]},
        )
        self.project_manager.save_asset_metadata(project_dir, asset)
        
        if job_id:
            log_job_progress(logger, job_id, 100, "complete")
            log_job_complete(logger, job_id, "character_image_generation", 0)
        
        log_generation(
            logger,
            "character_image",
            "local_python:diffusers",
            "sdxl-base",
            0,
            character_id=request.character_id,
            version=version,
        )
        
        return version_data
    
    async def approve_character(
        self,
        project_id: UUID,
        request: CharacterApprovalRequest,
    ) -> bool:
        """Approve or reject a character version."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        character = self.project_manager.load_character(project_dir, request.character_id)
        
        if not character:
            raise ValueError(f"Character not found: {request.character_id}")
        
        if request.approved:
            success = character.approve_version(request.version, request.approved_by)
            if success:
                character.lock_character()
                
                # Copy approved image to approved folder
                version_data = character.versions.get(request.version)
                if version_data and version_data.image_path:
                    approved_dir = project_dir / "characters" / request.character_id / "approved"
                    approved_dir.mkdir(parents=True, exist_ok=True)
                    
                    src = project_dir / version_data.image_path
                    dst = approved_dir / "reference.png"
                    import shutil
                    shutil.copy2(src, dst)
                    
                    character.reference_image = f"characters/{request.character_id}/approved/reference.png"
                
                self.project_manager.save_character(project_dir, character)
                
                # Save approval record
                from app.models.asset import ApprovalRecord, AssetType, ApprovalStatus
                approval = ApprovalRecord(
                    asset_type=AssetType.CHARACTER_BIBLE,
                    asset_id=request.character_id,
                    asset_version=request.version,
                    asset_path=version_data.image_path or "",
                    asset_hash="",
                    approved=True,
                    approved_by=request.approved_by,
                    notes=request.notes,
                    previous_version=character.approved_version,
                    changes=request.notes,
                )
                self.project_manager.save_approval(project_dir, approval)
                
                return True
        else:
            # Reject - just add notes
            version_data = character.versions.get(request.version)
            if version_data:
                version_data.metadata["rejected"] = True
                version_data.metadata["rejection_notes"] = request.notes
                version_data.metadata["rejected_by"] = request.approved_by
                self.project_manager.save_character(project_dir, character)
            
            # Save rejection record
            from app.models.asset import ApprovalRecord, AssetType, ApprovalStatus
            approval = ApprovalRecord(
                asset_type=AssetType.CHARACTER_BIBLE,
                asset_id=request.character_id,
                asset_version=request.version,
                asset_path="",
                asset_hash="",
                approved=False,
                approved_by=request.approved_by,
                notes=request.notes,
            )
            self.project_manager.save_approval(project_dir, approval)
        
        return False
    
    def get_character(self, project_id: UUID, character_id: str) -> Optional[CharacterBible]:
        """Get character bible."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        return self.project_manager.load_character(project_dir, character_id)
    
    def list_characters(self, project_id: UUID) -> List[Dict[str, Any]]:
        """List all characters for a project."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        return self.project_manager.load_characters_index(project_dir)
    
    async def upload_reference_image(
        self,
        project_id: UUID,
        character_id: str,
        version: str,
        image_path: str,
        set_as_canonical: bool = False,
    ) -> bool:
        """Upload a reference image for a character."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        character = self.project_manager.load_character(project_dir, character_id)
        
        if not character:
            raise ValueError(f"Character not found: {character_id}")
        
        # Copy image to references folder
        ref_dir = project_dir / "characters" / character_id / "references"
        ref_dir.mkdir(parents=True, exist_ok=True)
        
        src = Path(image_path)
        if not src.exists():
            raise FileNotFoundError(f"Source image not found: {image_path}")
        
        version_num = self.project_manager.get_next_version(
            project_dir, f"{character_id}_ref", "characters/references"
        )
        
        dst = ref_dir / f"ref_{version_num}{src.suffix}"
        import shutil
        shutil.copy2(src, dst)
        
        # Update version data
        version_data = character.versions.get(version)
        if version_data:
            version_data.reference_image_path = f"characters/{character_id}/references/{dst.name}"
            character.add_version(version_data)
        
        if set_as_canonical:
            # Copy to approved folder
            approved_dir = project_dir / "characters" / character_id / "approved"
            approved_dir.mkdir(parents=True, exist_ok=True)
            
            canonical_dst = approved_dir / "reference.png"
            shutil.copy2(src, canonical_dst)
            
            character.reference_image = f"characters/{character_id}/approved/reference.png"
            character.approved_version = version
            character.status = CharacterStatus.APPROVED
        
        self.project_manager.save_character(project_dir, character)
        return True