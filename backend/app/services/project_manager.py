"""
Project Manager service for the Cinematic Video Studio.
Handles project creation, loading, validation, and filesystem operations.
"""

import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from app.models.project import (
    ProjectManifest,
    ProjectStatus,
    ProjectCreate,
    ProjectUpdate,
    ProjectSummary,
    ProviderConfigMap,
    ModelConfiguration,
    WorkflowState,
    SourceInfo,
)
from app.models.transcript import TranscriptData, LanguageDetectionResult
from app.models.story import StoryGraph
from app.models.character import CharacterBible
from app.models.scene import Scene
from app.models.translation import LanguageWorkspace
from app.models.job import Job, JobStatus, JobType
from app.models.asset import AssetMetadata, AssetType, AssetIndex
from app.core.config import get_settings
from app.core.security import validate_project_path, sanitize_filename
from app.core.logging import get_project_logger, log_file_operation


class ProjectManager:
    """Manages project lifecycle and filesystem operations."""
    
    # Required project folder structure
    PROJECT_FOLDERS = [
        "source/source_media",
        "transcript",
        "story",
        "characters",
        "locations",
        "scenes",
        "languages",
        "prompts/story",
        "prompts/characters",
        "prompts/scenes",
        "prompts/images",
        "prompts/video",
        "prompts/audio",
        "prompts/music",
        "prompts/sfx",
        "images/characters",
        "images/locations",
        "images/scenes",
        "video/scenes",
        "video/silent_master",
        "video/previews",
        "audio/narration",
        "audio/dialogue",
        "audio/music",
        "audio/sfx",
        "audio/master",
        "output",
        "approvals",
        "logs",
        "exports",
        "jobs",
    ]
    
    # Supported languages
    SUPPORTED_LANGUAGES = [
        "en", "te", "hi", "kn", "ta", "ml", "bn", "fr", "de", "pt", "nl", "es"
    ]
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root).expanduser().resolve()
        self.project_root.mkdir(parents=True, exist_ok=True)
        self._settings = get_settings()
    
    def create_project(self, project_data: ProjectCreate) -> ProjectManifest:
        """Create a new project with full folder structure."""
        # Validate and sanitize project name
        project_name = sanitize_filename(project_data.name)
        project_id = uuid.uuid4()
        
        # Create project directory
        project_dir = self.project_root / project_name
        counter = 1
        original_name = project_name
        while project_dir.exists():
            project_name = f"{original_name}_{counter}"
            project_dir = self.project_root / project_name
            counter += 1
        
        project_dir.mkdir(parents=True)
        
        # Create folder structure
        for folder in self.PROJECT_FOLDERS:
            (project_dir / folder).mkdir(parents=True, exist_ok=True)
        
        # Create language subdirectories
        target_languages = project_data.target_languages or self.SUPPORTED_LANGUAGES
        for lang in target_languages:
            lang_dir = project_dir / "languages" / lang
            lang_dir.mkdir(parents=True, exist_ok=True)
            (lang_dir / "scenes").mkdir(parents=True, exist_ok=True)
            (lang_dir / "audio").mkdir(parents=True, exist_ok=True)
            (lang_dir / "prompts").mkdir(parents=True, exist_ok=True)
            
            # Create output directory for each language
            (project_dir / "output" / lang).mkdir(parents=True, exist_ok=True)
        
        # Create project manifest
        manifest = ProjectManifest(
            project_id=project_id,
            name=project_data.name,
            description=project_data.description,
            status=ProjectStatus.DRAFT,
            target_languages=target_languages,
            providers=project_data.providers or ProviderConfigMap(),
            model_configuration=project_data.model_configuration or ModelConfiguration(),
            workflow=WorkflowState(
                pending_stages=[
                    "source_import",
                    "transcript_processing",
                    "language_detection",
                    "story_analysis",
                    "character_extraction",
                    "character_prompt_generation",
                    "character_image_generation",
                    "character_approval",
                    "scene_generation",
                    "prompt_generation",
                    "translation",
                    "image_generation",
                    "video_generation",
                    "audio_generation",
                    "rendering",
                ]
            ),
            source=SourceInfo(),
        )
        
        # Save manifest
        self._save_manifest(project_dir, manifest)
        
        # Create initial asset index
        asset_index = AssetIndex(project_id=project_id)
        self._save_asset_index(project_dir, asset_index)
        
        # Create README
        self._create_readme(project_dir, manifest)
        
        return manifest
    
    def load_project(self, project_id: str) -> ProjectManifest:
        """Load project manifest from disk."""
        project_dir = self._find_project_dir(project_id)
        if not project_dir:
            raise FileNotFoundError(f"Project not found: {project_id}")
        
        manifest_path = project_dir / "project.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Project manifest not found: {manifest_path}")
        
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Convert UUID strings back to UUID objects
        if "project_id" in data and isinstance(data["project_id"], str):
            data["project_id"] = UUID(data["project_id"])
        
        return ProjectManifest(**data)
    
    def save_project(self, project_dir: Path, manifest: ProjectManifest) -> None:
        """Save project manifest to disk."""
        manifest.updated_at = datetime.utcnow()
        self._save_manifest(project_dir, manifest)
    
    def _save_manifest(self, project_dir: Path, manifest: ProjectManifest) -> None:
        """Save manifest to project.json."""
        manifest_path = project_dir / "project.json"
        
        # Convert to dict with UUID as string
        data = manifest.model_dump(mode="json")
        
        # Atomic write
        temp_path = manifest_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        temp_path.replace(manifest_path)
        
        log_file_operation(None, "write", str(manifest_path))
    
    def _save_asset_index(self, project_dir: Path, asset_index: AssetIndex) -> None:
        """Save asset index."""
        index_path = project_dir / "asset_index.json"
        temp_path = index_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(asset_index.model_dump(mode="json"), f, indent=2, ensure_ascii=False)
        temp_path.replace(index_path)
    
    def _create_readme(self, project_dir: Path, manifest: ProjectManifest) -> None:
        """Create README.md for the project."""
        readme_path = project_dir / "README.md"
        content = f"""# {manifest.name}

**Project ID:** {manifest.project_id}
**Created:** {manifest.created_at.isoformat()}
**Status:** {manifest.status.value}
**Source Language:** {manifest.source_language or "Not detected"}
**Target Languages:** {", ".join(manifest.target_languages)}

## Description
{manifest.description or "No description provided."}

## Project Structure
This project follows the Cinematic Video Studio standard structure:

```
{manifest.name}/
├── project.json          # This manifest
├── source/               # Source media & metadata
├── transcript/           # Transcript files
├── story/                # Story intelligence
├── characters/           # Character bible & assets
├── locations/            # Location references
├── scenes/               # Cinematic scenes
├── languages/            # Per-language workspaces
├── prompts/              # All generated prompts (versioned)
├── images/               # Generated images (versioned)
├── video/                # Video assets
├── audio/                # Audio assets
├── output/               # Final rendered videos
├── approvals/            # Approval records
├── logs/                 # Project-specific logs
├── exports/              # Export packages
└── jobs/                 # Job state persistence
```

## Workflow Stages
- [ ] Source Import
- [ ] Transcript Processing
- [ ] Language Detection
- [ ] Story Analysis
- [ ] Character Extraction
- [ ] Character Prompt Generation
- [ ] Character Image Generation
- [ ] Character Approval
- [ ] Scene Generation
- [ ] Prompt Generation
- [ ] Translation
- [ ] Image Generation
- [ ] Video Generation
- [ ] Audio Generation
- [ ] Rendering

---
*Generated by Cinematic Multi-Language Video Studio*
"""
        readme_path.write_text(content, encoding="utf-8")
    
    def _find_project_dir(self, project_id: str) -> Optional[Path]:
        """Find project directory by project_id."""
        # First try direct match by scanning project.json files
        for project_dir in self.project_root.iterdir():
            if project_dir.is_dir():
                manifest_path = project_dir / "project.json"
                if manifest_path.exists():
                    try:
                        with open(manifest_path, "r") as f:
                            data = json.load(f)
                        if data.get("project_id") == project_id:
                            return project_dir
                    except Exception:
                        continue
        return None
    
    def list_projects(self) -> List[ProjectSummary]:
        """List all projects in the project root."""
        projects = []
        
        for project_dir in self.project_root.iterdir():
            if not project_dir.is_dir():
                continue
            
            manifest_path = project_dir / "project.json"
            if not manifest_path.exists():
                continue
            
            try:
                with open(manifest_path, "r") as f:
                    data = json.load(f)
                
                # Convert to ProjectSummary
                manifest = ProjectManifest(**data)
                
                # Calculate progress
                total_stages = len(manifest.workflow.completed_stages) + len(manifest.workflow.pending_stages)
                completed = len(manifest.workflow.completed_stages)
                progress = (completed / total_stages * 100) if total_stages > 0 else 0
                
                summary = ProjectSummary(
                    project_id=manifest.project_id,
                    name=manifest.name,
                    description=manifest.description,
                    created_at=manifest.created_at,
                    updated_at=manifest.updated_at,
                    status=manifest.status,
                    source_language=manifest.source_language,
                    target_languages=manifest.target_languages,
                    current_stage=manifest.workflow.current_stage,
                    statistics=manifest.statistics,
                    progress_percent=progress,
                )
                projects.append(summary)
                
            except Exception as e:
                # Skip corrupted projects
                continue
        
        # Sort by updated_at descending
        projects.sort(key=lambda p: p.updated_at, reverse=True)
        return projects
    
    def delete_project(self, project_id: str) -> bool:
        """Delete a project and all its files."""
        project_dir = self._find_project_dir(project_id)
        if not project_dir:
            return False
        
        try:
            shutil.rmtree(project_dir)
            return True
        except Exception:
            return False
    
    def get_project_path(self, project_id: str) -> Path:
        """Get the project directory path."""
        project_dir = self._find_project_dir(project_id)
        if not project_dir:
            raise FileNotFoundError(f"Project not found: {project_id}")
        return project_dir
    
    def validate_project_structure(self, project_dir: Path) -> Tuple[bool, List[str]]:
        """Validate that project has all required folders."""
        errors = []
        
        for folder in self.PROJECT_FOLDERS:
            folder_path = project_dir / folder
            if not folder_path.exists():
                errors.append(f"Missing folder: {folder}")
        
        # Check for project.json
        if not (project_dir / "project.json").exists():
            errors.append("Missing project.json")
        
        return len(errors) == 0, errors
    
    def repair_project_structure(self, project_dir: Path) -> List[str]:
        """Repair missing folders in project structure."""
        created = []
        
        for folder in self.PROJECT_FOLDERS:
            folder_path = project_dir / folder
            if not folder_path.exists():
                folder_path.mkdir(parents=True, exist_ok=True)
                created.append(folder)
        
        # Create language directories if missing
        manifest = self.load_project(str(project_dir.name))
        for lang in manifest.target_languages:
            lang_dir = project_dir / "languages" / lang
            if not lang_dir.exists():
                lang_dir.mkdir(parents=True, exist_ok=True)
                (lang_dir / "scenes").mkdir(parents=True, exist_ok=True)
                (lang_dir / "audio").mkdir(parents=True, exist_ok=True)
                (lang_dir / "prompts").mkdir(parents=True, exist_ok=True)
                created.append(f"languages/{lang}")
            
            output_dir = project_dir / "output" / lang
            if not output_dir.exists():
                output_dir.mkdir(parents=True, exist_ok=True)
                created.append(f"output/{lang}")
        
        return created
    
    # Transcript operations
    
    def save_transcript(self, project_dir: Path, transcript: TranscriptData) -> None:
        """Save transcript data."""
        transcript_dir = project_dir / "transcript"
        
        # Save normalized JSON
        transcript_path = transcript_dir / "normalized.json"
        temp_path = transcript_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(transcript.model_dump(mode="json"), f, indent=2, ensure_ascii=False)
        temp_path.replace(transcript_path)
        
        # Save plain text
        text_path = transcript_dir / "normalized.txt"
        text_path.write_text(transcript.get_text(), encoding="utf-8")
        
        # Save segments
        segments_path = transcript_dir / "segments.json"
        with open(segments_path.with_suffix(".tmp"), "w", encoding="utf-8") as f:
            json.dump(
                {"segments": [s.model_dump(mode="json") for s in transcript.segments]},
                f, indent=2, ensure_ascii=False
            )
        segments_path.with_suffix(".tmp").replace(segments_path)
        
        log_file_operation(None, "write", str(transcript_path))
    
    def load_transcript(self, project_dir: Path) -> Optional[TranscriptData]:
        """Load transcript data."""
        transcript_path = project_dir / "transcript" / "normalized.json"
        if not transcript_path.exists():
            return None
        
        with open(transcript_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return TranscriptData(**data)
    
    def save_language_detection(self, project_dir: Path, detection: LanguageDetectionResult) -> None:
        """Save language detection result."""
        detection_path = project_dir / "transcript" / "language_detection.json"
        temp_path = detection_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(detection.model_dump(mode="json"), f, indent=2, ensure_ascii=False)
        temp_path.replace(detection_path)
    
    def load_language_detection(self, project_dir: Path) -> Optional[LanguageDetectionResult]:
        """Load language detection result."""
        detection_path = project_dir / "transcript" / "language_detection.json"
        if not detection_path.exists():
            return None
        
        with open(detection_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return LanguageDetectionResult(**data)
    
    # Story operations
    
    def save_story(self, project_dir: Path, story: StoryGraph) -> None:
        """Save story graph."""
        story_dir = project_dir / "story"
        
        # Save main story graph
        story_path = story_dir / "story.json"
        temp_path = story_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(story.model_dump(mode="json"), f, indent=2, ensure_ascii=False)
        temp_path.replace(story_path)
        
        # Save acts
        acts_path = story_dir / "acts.json"
        with open(acts_path.with_suffix(".tmp"), "w", encoding="utf-8") as f:
            json.dump(
                {"acts": [a.model_dump(mode="json") for a in story.acts]},
                f, indent=2, ensure_ascii=False
            )
        acts_path.with_suffix(".tmp").replace(acts_path)
        
        # Save events
        events_path = story_dir / "events.json"
        with open(events_path.with_suffix(".tmp"), "w", encoding="utf-8") as f:
            json.dump(
                {"events": [e.model_dump(mode="json") for e in story.events]},
                f, indent=2, ensure_ascii=False
            )
        events_path.with_suffix(".tmp").replace(events_path)
        
        # Save themes
        themes_path = story_dir / "themes.json"
        with open(themes_path.with_suffix(".tmp"), "w", encoding="utf-8") as f:
            json.dump(
                {"themes": [t.model_dump(mode="json") for t in story.themes]},
                f, indent=2, ensure_ascii=False
            )
        themes_path.with_suffix(".tmp").replace(themes_path)
        
        # Save relationships
        rel_path = story_dir / "relationships.json"
        with open(rel_path.with_suffix(".tmp"), "w", encoding="utf-8") as f:
            json.dump(
                {"relationships": [r.model_dump(mode="json") for r in story.relationships]},
                f, indent=2, ensure_ascii=False
            )
        rel_path.with_suffix(".tmp").replace(rel_path)
        
        log_file_operation(None, "write", str(story_path))
    
    def load_story(self, project_dir: Path) -> Optional[StoryGraph]:
        """Load story graph."""
        story_path = project_dir / "story" / "story.json"
        if not story_path.exists():
            return None
        
        with open(story_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return StoryGraph(**data)
    
    # Character operations
    
    def save_character(self, project_dir: Path, character: CharacterBible) -> None:
        """Save character bible."""
        char_dir = project_dir / "characters" / character.character_id
        char_dir.mkdir(parents=True, exist_ok=True)
        
        # Save main character file
        char_path = char_dir / "character.json"
        temp_path = char_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(character.model_dump(mode="json"), f, indent=2, ensure_ascii=False)
        temp_path.replace(char_path)
        
        # Update characters index
        self._update_characters_index(project_dir)
        
        log_file_operation(None, "write", str(char_path))
    
    def load_character(self, project_dir: Path, character_id: str) -> Optional[CharacterBible]:
        """Load character bible."""
        char_path = project_dir / "characters" / character_id / "character.json"
        if not char_path.exists():
            return None
        
        with open(char_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return CharacterBible(**data)
    
    def _update_characters_index(self, project_dir: Path) -> None:
        """Update characters.json index."""
        characters_dir = project_dir / "characters"
        index_path = characters_dir / "characters.json"
        
        characters = []
        for char_dir in characters_dir.iterdir():
            if char_dir.is_dir() and char_dir.name != "approved.json":
                char_path = char_dir / "character.json"
                if char_path.exists():
                    try:
                        with open(char_path, "r") as f:
                            data = json.load(f)
                        characters.append({
                            "character_id": data.get("character_id"),
                            "canonical_name": data.get("canonical_name"),
                            "status": data.get("status"),
                            "current_version": data.get("current_version"),
                            "approved_version": data.get("approved_version"),
                            "approved_at": data.get("approved_at"),
                            "approved_by": data.get("approved_by"),
                            "reference_image": data.get("reference_image"),
                            "scenes": data.get("scenes", []),
                        })
                    except Exception:
                        continue
        
        with open(index_path.with_suffix(".tmp"), "w", encoding="utf-8") as f:
            json.dump({"characters": characters}, f, indent=2, ensure_ascii=False)
        index_path.with_suffix(".tmp").replace(index_path)
    
    def load_characters_index(self, project_dir: Path) -> List[Dict[str, Any]]:
        """Load characters index."""
        index_path = project_dir / "characters" / "characters.json"
        if not index_path.exists():
            return []
        
        with open(index_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return data.get("characters", [])
    
    # Scene operations
    
    def save_scene(self, project_dir: Path, scene: Scene) -> None:
        """Save scene."""
        scene_dir = project_dir / "scenes" / scene.scene_id
        scene_dir.mkdir(parents=True, exist_ok=True)
        
        scene_path = scene_dir / "scene.json"
        temp_path = scene_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(scene.model_dump(mode="json"), f, indent=2, ensure_ascii=False)
        temp_path.replace(scene_path)
        
        # Update scenes index
        self._update_scenes_index(project_dir)
        
        log_file_operation(None, "write", str(scene_path))
    
    def load_scene(self, project_dir: Path, scene_id: str) -> Optional[Scene]:
        """Load scene."""
        scene_path = project_dir / "scenes" / scene_id / "scene.json"
        if not scene_path.exists():
            return None
        
        with open(scene_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return Scene(**data)
    
    def _update_scenes_index(self, project_dir: Path) -> None:
        """Update scenes.json index."""
        scenes_dir = project_dir / "scenes"
        index_path = scenes_dir / "scenes.json"
        
        scenes = []
        for scene_dir in scenes_dir.iterdir():
            if scene_dir.is_dir():
                scene_path = scene_dir / "scene.json"
                if scene_path.exists():
                    try:
                        with open(scene_path, "r") as f:
                            data = json.load(f)
                        scenes.append({
                            "scene_id": data.get("scene_id"),
                            "act_id": data.get("act_id"),
                            "order": data.get("order"),
                            "title": data.get("title"),
                            "duration_seconds": data.get("duration_seconds"),
                            "source_segments": data.get("source_segments", []),
                            "status": data.get("status"),
                            "current_version": data.get("current_version"),
                            "approved_version": data.get("approved_version"),
                            "characters": data.get("characters", []),
                            "location_id": data.get("location", {}).get("location_id"),
                            "visual_style": data.get("visual_style"),
                            "has_video": data.get("video_path") is not None,
                            "has_audio": bool(data.get("audio_paths")),
                        })
                    except Exception:
                        continue
        
        # Sort by order
        scenes.sort(key=lambda s: s.get("order", 0))
        
        with open(index_path.with_suffix(".tmp"), "w", encoding="utf-8") as f:
            json.dump({"scenes": scenes}, f, indent=2, ensure_ascii=False)
        index_path.with_suffix(".tmp").replace(index_path)
    
    def load_scenes_index(self, project_dir: Path) -> List[Dict[str, Any]]:
        """Load scenes index."""
        index_path = project_dir / "scenes" / "scenes.json"
        if not index_path.exists():
            return []
        
        with open(index_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return data.get("scenes", [])
    
    # Translation operations
    
    def save_translation(self, project_dir: Path, language: str, translation: LanguageWorkspace) -> None:
        """Save translation workspace for a language."""
        lang_dir = project_dir / "languages" / language
        lang_dir.mkdir(parents=True, exist_ok=True)
        
        # Save scenes
        scenes_dir = lang_dir / "scenes"
        scenes_dir.mkdir(parents=True, exist_ok=True)
        
        for scene_id, scene_trans in translation.scenes.items():
            scene_path = scenes_dir / f"{scene_id}.json"
            temp_path = scene_path.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(scene_trans.model_dump(mode="json"), f, indent=2, ensure_ascii=False)
            temp_path.replace(scene_path)
        
        # Save semantic review
        review_path = lang_dir / "semantic_review.json"
        with open(review_path.with_suffix(".tmp"), "w", encoding="utf-8") as f:
            json.dump(translation.semantic_review.model_dump(mode="json"), f, indent=2, ensure_ascii=False)
        review_path.with_suffix(".tmp").replace(review_path)
        
        # Save voice prompts
        prompts_path = lang_dir / "prompts" / "voice_prompts.json"
        prompts_path.parent.mkdir(parents=True, exist_ok=True)
        with open(prompts_path.with_suffix(".tmp"), "w", encoding="utf-8") as f:
            json.dump(translation.voice_prompts, f, indent=2, ensure_ascii=False)
        prompts_path.with_suffix(".tmp").replace(prompts_path)
        
        log_file_operation(None, "write", str(lang_dir))
    
    def load_translation(self, project_dir: Path, language: str) -> Optional[LanguageWorkspace]:
        """Load translation workspace for a language."""
        lang_dir = project_dir / "languages" / language
        if not lang_dir.exists():
            return None
        
        # Load scenes
        scenes_dir = lang_dir / "scenes"
        scenes = {}
        if scenes_dir.exists():
            for scene_file in scenes_dir.glob("*.json"):
                try:
                    with open(scene_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    from app.models.translation import SceneTranslation
                    scenes[scene_file.stem] = SceneTranslation(**data)
                except Exception:
                    continue
        
        # Load semantic review
        review_path = lang_dir / "semantic_review.json"
        semantic_review = None
        if review_path.exists():
            with open(review_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            from app.models.translation import SemanticReview
            semantic_review = SemanticReview(**data)
        
        # Load voice prompts
        prompts_path = lang_dir / "prompts" / "voice_prompts.json"
        voice_prompts = {}
        if prompts_path.exists():
            with open(prompts_path, "r", encoding="utf-8") as f:
                voice_prompts = json.load(f)
        
        return LanguageWorkspace(
            language=language,
            scenes=scenes,
            semantic_review=semantic_review or SemanticReview(),
            voice_prompts=voice_prompts,
        )
    
    # Job operations
    
    def save_job(self, project_dir: Path, job: Job) -> None:
        """Save job state."""
        jobs_dir = project_dir / "jobs"
        jobs_dir.mkdir(parents=True, exist_ok=True)
        
        job_path = jobs_dir / f"{job.job_id}.json"
        temp_path = job_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(job.model_dump(mode="json"), f, indent=2, ensure_ascii=False)
        temp_path.replace(job_path)
    
    def load_job(self, project_dir: Path, job_id: str) -> Optional[Job]:
        """Load job state."""
        job_path = project_dir / "jobs" / f"{job_id}.json"
        if not job_path.exists():
            return None
        
        with open(job_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return Job(**data)
    
    def list_jobs(self, project_dir: Path) -> List[Job]:
        """List all jobs for a project."""
        jobs_dir = project_dir / "jobs"
        if not jobs_dir.exists():
            return []
        
        jobs = []
        for job_file in jobs_dir.glob("*.json"):
            try:
                with open(job_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                jobs.append(Job(**data))
            except Exception:
                continue
        
        # Sort by created_at descending
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        return jobs
    
    # Asset operations
    
    def save_asset_metadata(self, project_dir: Path, asset: AssetMetadata) -> None:
        """Save asset metadata."""
        asset_index = self.load_asset_index(project_dir)
        asset_index.add_asset(asset)
        self._save_asset_index(project_dir, asset_index)
        
        # Also save individual metadata file
        meta_path = project_dir / asset.file_path.replace(".", "_meta.") + ".json"
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        with open(meta_path.with_suffix(".tmp"), "w", encoding="utf-8") as f:
            json.dump(asset.model_dump(mode="json"), f, indent=2, ensure_ascii=False)
        meta_path.with_suffix(".tmp").replace(meta_path)
    
    def load_asset_index(self, project_dir: Path) -> AssetIndex:
        """Load asset index."""
        index_path = project_dir / "asset_index.json"
        if not index_path.exists():
            # Try to get project_id from manifest
            manifest_path = project_dir / "project.json"
            project_id = UUID("00000000-0000-0000-0000-000000000000")
            if manifest_path.exists():
                with open(manifest_path, "r") as f:
                    data = json.load(f)
                project_id = UUID(data.get("project_id", str(project_id)))
            return AssetIndex(project_id=project_id)
        
        with open(index_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return AssetIndex(**data)
    
    # Approval operations
    
    def save_approval(self, project_dir: Path, approval) -> None:
        """Save approval record."""
        approvals_dir = project_dir / "approvals"
        approvals_dir.mkdir(parents=True, exist_ok=True)
        
        approval_path = approvals_dir / f"{approval.asset_type.value}_{approval.asset_id}.json"
        temp_path = approval_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(approval.model_dump(mode="json"), f, indent=2, ensure_ascii=False)
        temp_path.replace(approval_path)
    
    def load_approvals(self, project_dir: Path) -> List[Any]:
        """Load all approval records."""
        approvals_dir = project_dir / "approvals"
        if not approvals_dir.exists():
            return []
        
        approvals = []
        for approval_file in approvals_dir.glob("*.json"):
            try:
                with open(approval_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                approvals.append(data)
            except Exception:
                continue
        
        return approvals
    
    # Utility methods
    
    def get_next_version(self, project_dir: Path, base_name: str, folder: str) -> str:
        """Get next version number for a file."""
        folder_path = project_dir / folder
        if not folder_path.exists():
            return "v001"
        
        existing = list(folder_path.glob(f"{base_name}_v*.*"))
        max_version = 0
        for f in existing:
            try:
                version_str = f.stem.split("_v")[-1]
                version = int(version_str[:3])
                max_version = max(max_version, version)
            except Exception:
                continue
        
        return f"v{max_version + 1:03d}"
    
    def compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of a file."""
        import hashlib
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()