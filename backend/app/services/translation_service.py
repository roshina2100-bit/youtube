"""
Translation Service for the Cinematic Video Studio.
Handles context-aware translation, semantic review, and multi-language management.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.models.translation import (
    SceneTranslation, SemanticReview, TranslationStatus,
    LanguageWorkspace, TranslationRequest, BatchTranslationRequest,
    SemanticReviewRequest, SemanticReviewResult
)
from app.models.scene import Scene
from app.models.story import StoryGraph
from app.models.provider import ProviderType
from app.providers.registry import ProviderRegistry
from app.services.project_manager import ProjectManager
from app.core.logging import get_project_logger, log_job_start, log_job_progress, log_job_complete, log_job_error, log_generation


class TranslationService:
    """Service for translation and semantic review."""
    
    def __init__(self, project_manager: ProjectManager, provider_registry: ProviderRegistry):
        self.project_manager = project_manager
        self.provider_registry = provider_registry
    
    async def translate_project(
        self,
        project_id: UUID,
        target_languages: List[str],
        provider_name: str = "local_python",
        model_name: str = "nllb-200-distilled-600M",
        job_id: Optional[str] = None
    ) -> Dict[str, LanguageWorkspace]:
        """Translate all scenes for all target languages."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        logger = get_project_logger(str(project_id), self.project_manager.project_root)
        
        if job_id:
            log_job_start(logger, job_id, "translation")
        
        # Load scenes
        scenes = self.project_manager.load_scenes_index(project_dir)
        story = self.project_manager.load_story(project_dir)
        
        if not story:
            raise ValueError("Story graph not found")
        
        # Get source language
        source_language = story.source_language or "en"
        
        results = {}
        total_work = len(target_languages) * len(scenes)
        completed = 0
        
        for lang in target_languages:
            if lang == source_language:
                # Skip source language
                continue
            
            if job_id:
                log_job_progress(logger, job_id, int((completed / total_work) * 100), f"translate_{lang}")
            
            # Load or create language workspace
            workspace = self.project_manager.load_translation(project_dir, lang)
            if not workspace:
                workspace = LanguageWorkspace(language=lang)
            
            # Translate each scene
            for scene_info in scenes:
                scene = self.project_manager.load_scene(project_dir, scene_info["scene_id"])
                if not scene:
                    continue
                
                # Translate scene
                translation = await self._translate_scene(
                    project_id, scene, source_language, lang,
                    provider_name, model_name, story
                )
                
                workspace.add_scene_translation(translation)
                completed += 1
                
                if job_id:
                    progress = int((completed / total_work) * 100)
                    log_job_progress(logger, job_id, progress, f"translate_{lang}_{scene.scene_id}")
            
            # Save workspace
            self.project_manager.save_translation(project_dir, lang, workspace)
            results[lang] = workspace
        
        if job_id:
            log_job_progress(logger, job_id, 100, "complete")
            log_job_complete(logger, job_id, "translation", 0)
        
        return results
    
    async def _translate_scene(
        self,
        project_id: UUID,
        scene: Scene,
        source_lang: str,
        target_lang: str,
        provider_name: str,
        model_name: str,
        story_graph: StoryGraph
    ) -> SceneTranslation:
        """Translate a single scene with full context."""
        provider = self.provider_registry.get_provider(
            ProviderType.TRANSLATION, provider_name, model_name
        )
        
        if not provider:
            await self.provider_registry.load_provider(
                ProviderType.TRANSLATION, provider_name, model_name
            )
            provider = self.provider_registry.get_provider(
                ProviderType.TRANSLATION, provider_name, model_name
            )
        
        if not provider or not provider.is_available():
            raise RuntimeError(f"Translation provider not available: {provider_name}:{model_name}")
        
        # Build context
        context = self._build_translation_context(scene, story_graph)
        
        # Translate narration
        narration_result = await provider.translate_with_context(
            text=scene.narration,
            source_lang=source_lang,
            target_lang=target_lang,
            context=context,
        )
        
        # Translate dialogue
        translated_dialogue = []
        for d in scene.dialogue:
            dlg_result = await provider.translate_with_context(
                text=d.get("text", ""),
                source_lang=source_lang,
                target_lang=target_lang,
                context={**context, "speaker": d.get("speaker", "")},
            )
            translated_dialogue.append({
                "speaker": d.get("speaker", ""),
                "text": dlg_result.data if dlg_result.success else d.get("text", ""),
                "emotion": d.get("emotion", ""),
            })
        
        # Translate character names
        character_names = {}
        for sc in scene.characters:
            char = self.project_manager.load_character(
                self.project_manager.get_project_path(str(project_id)), sc.character_id
            )
            if char:
                name_result = await provider.translate_with_context(
                    text=char.canonical_name,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    context={**context, "type": "character_name"},
                )
                character_names[sc.character_id] = name_result.data if name_result.success else char.canonical_name
        
        # Translate location name
        location_result = await provider.translate_with_context(
            text=scene.location.name,
            source_lang=source_lang,
            target_lang=target_lang,
            context={**context, "type": "location_name"},
        )
        
        return SceneTranslation(
            scene_id=scene.scene_id,
            language=target_lang,
            source_language=source_lang,
            narration=narration_result.data if narration_result.success else scene.narration,
            dialogue=translated_dialogue,
            character_names=character_names,
            location_name=location_result.data if location_result.success else scene.location.name,
            cultural_notes=context.get("cultural_notes", ""),
            translated_by=f"{provider_name}:{model_name}",
        )
    
    def _build_translation_context(self, scene: Scene, story_graph: StoryGraph) -> Dict[str, Any]:
        """Build context for translation."""
        # Find previous and next scenes
        prev_scene = None
        next_scene = None
        scenes = self.project_manager.load_scenes_index(self.project_manager.get_project_path(str(scene.scene_id.split('_')[0] + '_' + scene.scene_id.split('_')[1]))) if '_' in scene.scene_id else []
        
        # Simplified - would need proper scene ordering
        context = {
            "scene_description": f"{scene.title}: {scene.action}",
            "characters": [sc.character_id for sc in scene.characters],
            "location": scene.location.name,
            "emotion": scene.emotion,
            "visual_style": scene.visual_style,
            "cultural_notes": story_graph.cultural_context.historical_notes if story_graph.cultural_context else "",
        }
        
        return context
    
    async def translate_scene(
        self,
        project_id: UUID,
        scene_id: str,
        target_language: str,
        provider_name: str = "local_python",
        model_name: str = "nllb-200-distilled-600M",
    ) -> SceneTranslation:
        """Translate a single scene to a target language."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        scene = self.project_manager.load_scene(project_dir, scene_id)
        
        if not scene:
            raise ValueError(f"Scene not found: {scene_id}")
        
        story = self.project_manager.load_story(project_dir)
        source_language = story.source_language if story else "en"
        
        return await self._translate_scene(
            project_id, scene, source_language, target_language,
            provider_name, model_name, story
        )
    
    async def review_translation(
        self,
        project_id: UUID,
        scene_id: str,
        language: str,
        provider_name: str = "local_python",
        model_name: str = "llama-3-8b-instruct",
    ) -> SemanticReview:
        """Perform semantic review of a translation."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        logger = get_project_logger(str(project_id), self.project_manager.project_root)
        
        # Load source scene and translation
        scene = self.project_manager.load_scene(project_dir, scene_id)
        workspace = self.project_manager.load_translation(project_dir, language)
        
        if not scene or not workspace:
            raise ValueError("Scene or translation not found")
        
        translation = workspace.get_scene_translation(scene_id)
        if not translation:
            raise ValueError(f"Translation not found for scene {scene_id} in {language}")
        
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
        
        # Build review prompt
        prompt = self._build_review_prompt(scene, translation)
        
        result = await provider.generate_structured(
            prompt=prompt,
            schema=self._get_review_schema(),
            max_tokens=4096,
            temperature=0.2,
        )
        
        if not result.success:
            raise RuntimeError(f"Semantic review failed: {result.error}")
        
        review_data = result.data
        review = SemanticReview(**review_data)
        
        # Update translation
        translation.semantic_review = review
        workspace.add_scene_translation(translation)
        self.project_manager.save_translation(project_dir, language, workspace)
        
        return review
    
    def _build_review_prompt(self, scene: Scene, translation: SceneTranslation) -> str:
        """Build prompt for semantic review."""
        return f"""Perform a semantic review of the following translation.

ORIGINAL SCENE ({scene.scene_id}):
- Title: {scene.title}
- Narration: {scene.narration}
- Dialogue: {json.dumps(scene.dialogue, ensure_ascii=False)}
- Characters: {[sc.character_id for sc in scene.characters]}
- Location: {scene.location.name}
- Action: {scene.action}
- Emotion: {scene.emotion}

TRANSLATED SCENE ({translation.language}):
- Narration: {translation.narration}
- Dialogue: {json.dumps(translation.dialogue, ensure_ascii=False)}
- Character Names: {json.dumps(translation.character_names, ensure_ascii=False)}
- Location Name: {translation.location_name}
- Cultural Notes: {translation.cultural_notes}

Check the following semantic preservation criteria:
1. events_preserved - Are all events from the original preserved?
2. characters_preserved - Are all characters correctly represented?
3. relationships_preserved - Are character relationships maintained?
4. emotion_preserved - Is the emotional tone preserved?
5. intent_preserved - Is the narrative intent preserved?
6. facts_preserved - Are factual details preserved?
7. cultural_meaning_preserved - Is cultural meaning preserved?
8. timing_preserved - Is the timing/pacing preserved?

For each check, return: passed (boolean), details (string), severity (info/warning/error).
Also list any issues and flags.
Return ONLY valid JSON matching the provided schema.
"""
    
    def _get_review_schema(self) -> Dict[str, Any]:
        """Get JSON schema for semantic review."""
        return {
            "type": "object",
            "properties": {
                "reviewed": {"type": "boolean"},
                "checks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "check_name": {"type": "string"},
                            "passed": {"type": "boolean"},
                            "details": {"type": "string"},
                            "severity": {"type": "string", "enum": ["info", "warning", "error"]},
                        },
                        "required": ["check_name", "passed", "details", "severity"]
                    }
                },
                "issues": {"type": "array", "items": {"type": "string"}},
                "flags": {"type": "array", "items": {"type": "string"}},
                "status": {"type": "string", "enum": ["draft", "translated", "review_required", "approved"]},
                "notes": {"type": "string"},
            },
            "required": ["reviewed", "checks", "issues", "flags", "status"]
        }
    
    def get_translation(self, project_id: UUID, language: str) -> Optional[LanguageWorkspace]:
        """Get translation workspace for a language."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        return self.project_manager.load_translation(project_dir, language)
    
    def get_scene_translation(self, project_id: UUID, scene_id: str, language: str) -> Optional[SceneTranslation]:
        """Get translation for a specific scene in a language."""
        workspace = self.get_translation(project_id, language)
        if not workspace:
            return None
        return workspace.get_scene_translation(scene_id)
    
    def list_translations(self, project_id: UUID) -> Dict[str, LanguageWorkspace]:
        """List all translation workspaces for a project."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        languages_dir = project_dir / "languages"
        
        if not languages_dir.exists():
            return {}
        
        results = {}
        for lang_dir in languages_dir.iterdir():
            if lang_dir.is_dir():
                workspace = self.project_manager.load_translation(project_dir, lang_dir.name)
                if workspace:
                    results[lang_dir.name] = workspace
        
        return results
    
    async def approve_translation(
        self,
        project_id: UUID,
        scene_id: str,
        language: str,
        approved: bool,
        approved_by: str = "user",
        notes: str = "",
    ) -> bool:
        """Approve or reject a scene translation."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        workspace = self.project_manager.load_translation(project_dir, language)
        
        if not workspace:
            raise ValueError(f"Translation workspace not found for {language}")
        
        translation = workspace.get_scene_translation(scene_id)
        if not translation:
            raise ValueError(f"Translation not found for scene {scene_id} in {language}")
        
        if approved:
            translation.semantic_review.status = TranslationStatus.APPROVED
            translation.semantic_review.reviewed = True
            translation.semantic_review.reviewed_by = approved_by
            translation.semantic_review.reviewed_at = time.time()
            translation.semantic_review.notes = notes
        else:
            translation.semantic_review.status = TranslationStatus.REVIEW_REQUIRED
            translation.semantic_review.issues.append(notes)
        
        workspace.add_scene_translation(translation)
        self.project_manager.save_translation(project_dir, language, workspace)
        
        # Save approval record
        from app.models.asset import ApprovalRecord, AssetType
        approval = ApprovalRecord(
            asset_type=AssetType.TRANSLATION,
            asset_id=f"{scene_id}_{language}",
            asset_version=translation.version,
            asset_path=f"languages/{language}/scenes/{scene_id}.json",
            asset_hash="",
            approved=approved,
            approved_by=approved_by,
            notes=notes,
        )
        self.project_manager.save_approval(project_dir, approval)
        
        return True