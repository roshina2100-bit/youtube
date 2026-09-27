"""
Story Service for the Cinematic Video Studio.
Handles story analysis, story graph creation, and story intelligence.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.models.story import (
    StoryGraph, Act, Event, Theme, CharacterRef, LocationRef, Relationship,
    CulturalContext, StoryAnalysisRequest, StoryAnalysisResult
)
from app.models.transcript import TranscriptData
from app.models.provider import ProviderType
from app.providers.registry import ProviderRegistry
from app.services.project_manager import ProjectManager
from app.core.logging import get_project_logger, log_job_start, log_job_progress, log_job_complete, log_job_error


class StoryService:
    """Service for story analysis and story graph management."""
    
    def __init__(self, project_manager: ProjectManager, provider_registry: ProviderRegistry):
        self.project_manager = project_manager
        self.provider_registry = provider_registry
    
    async def analyze_story(
        self, 
        project_id: UUID, 
        request: StoryAnalysisRequest,
        job_id: Optional[str] = None
    ) -> StoryAnalysisResult:
        """Analyze transcript and create story graph."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        logger = get_project_logger(str(project_id), self.project_manager.project_root)
        
        if job_id:
            log_job_start(logger, job_id, "story_analysis")
        
        start_time = time.time()
        
        try:
            # Load transcript
            transcript = self.project_manager.load_transcript(project_dir)
            if not transcript:
                raise ValueError("No transcript found for project")
            
            # Get provider
            provider_name = request.provider or "local_python"
            model_name = request.model or "llama-3-8b-instruct"
            
            provider = self.provider_registry.get_provider(
                ProviderType.LLM, provider_name, model_name
            )
            
            if not provider:
                # Try to load
                await self.provider_registry.load_provider(
                    ProviderType.LLM, provider_name, model_name
                )
                provider = self.provider_registry.get_provider(
                    ProviderType.LLM, provider_name, model_name
                )
            
            if not provider or not provider.is_available():
                raise RuntimeError(f"LLM provider not available: {provider_name}:{model_name}")
            
            if job_id:
                log_job_progress(logger, job_id, 25, "load_transcript")
            
            # Build analysis prompt
            prompt = self._build_story_analysis_prompt(transcript, request.language)
            
            if job_id:
                log_job_progress(logger, job_id, 50, "generate_story")
            
            # Generate story analysis
            result = await provider.generate_structured(
                prompt=prompt,
                schema=self._get_story_schema(),
                max_tokens=8192,
                temperature=0.3,
            )
            
            if job_id:
                log_job_progress(logger, job_id, 75, "parse_story")
            
            if not result.success:
                raise RuntimeError(f"Story analysis failed: {result.error}")
            
            # Parse result into StoryGraph
            story_graph = self._parse_story_result(result.data, request.language)
            
            # Save story
            self.project_manager.save_story(project_dir, story_graph)
            
            if job_id:
                log_job_progress(logger, job_id, 100, "save_story")
            
            duration = time.time() - start_time
            
            if job_id:
                log_job_complete(logger, job_id, "story_analysis", duration)
            
            return StoryAnalysisResult(
                story_graph=story_graph,
                processing_time_seconds=duration,
                provider=f"{provider_name}:{model_name}",
                model=model_name,
                token_usage=result.metadata.get("tokens_generated", 0),
            )
            
        except Exception as e:
            duration = time.time() - start_time
            if job_id:
                log_job_error(logger, job_id, "story_analysis", e)
            raise
    
    def _build_story_analysis_prompt(self, transcript: TranscriptData, language: str) -> str:
        """Build prompt for story analysis."""
        transcript_text = transcript.get_text(include_timestamps=True)
        
        return f"""Analyze the following transcript and create a comprehensive story graph.
The transcript is in {language} language.

TRANSCRIPT:
{transcript_text}

Create a detailed story graph with the following structure:
1. Title and summary
2. Acts (major story divisions)
3. Characters (all named characters with roles, descriptions, relationships)
4. Locations (all settings with descriptions)
5. Events (chronological timeline)
6. Themes (major themes with prominence)
7. Relationships (between characters)
8. Cultural context (historical, religious, cultural elements)

Return ONLY valid JSON matching the provided schema. Do not include any explanatory text.
"""
    
    def _get_story_schema(self) -> Dict[str, Any]:
        """Get JSON schema for story graph."""
        return {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "summary": {"type": "string"},
                "source_language": {"type": "string"},
                "acts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "act_id": {"type": "string"},
                            "title": {"type": "string"},
                            "order": {"type": "integer"},
                            "summary": {"type": "string"},
                            "scenes": {"type": "array", "items": {"type": "string"}},
                            "characters": {"type": "array", "items": {"type": "string"}},
                            "locations": {"type": "array", "items": {"type": "string"}},
                            "themes": {"type": "array", "items": {"type": "string"}},
                            "start_time": {"type": "number"},
                            "end_time": {"type": "number"},
                        },
                        "required": ["act_id", "title", "order", "summary"]
                    }
                },
                "characters": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "character_id": {"type": "string"},
                            "canonical_name": {"type": "string"},
                            "aliases": {"type": "array", "items": {"type": "string"}},
                            "role": {"type": "string"},
                            "importance": {"type": "string"},
                            "first_appearance": {"type": "string"},
                            "description": {"type": "string"},
                        },
                        "required": ["character_id", "canonical_name", "role"]
                    }
                },
                "locations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "location_id": {"type": "string"},
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "type": {"type": "string"},
                            "scenes": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["location_id", "name"]
                    }
                },
                "events": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "event_id": {"type": "string"},
                            "time": {"type": "string"},
                            "description": {"type": "string"},
                            "scene_id": {"type": "string"},
                            "characters": {"type": "array", "items": {"type": "string"}},
                            "location_id": {"type": "string"},
                            "importance": {"type": "string"},
                        },
                        "required": ["event_id", "time", "description"]
                    }
                },
                "themes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "prominence": {"type": "number"},
                            "description": {"type": "string"},
                            "related_characters": {"type": "array", "items": {"type": "string"}},
                            "related_scenes": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["name", "prominence"]
                    }
                },
                "relationships": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "character_id": {"type": "string"},
                            "related_character_id": {"type": "string"},
                            "type": {"type": "string"},
                            "description": {"type": "string"},
                            "strength": {"type": "number"},
                        },
                        "required": ["character_id", "related_character_id", "type"]
                    }
                },
                "cultural_context": {
                    "type": "object",
                    "properties": {
                        "period": {"type": "string"},
                        "culture": {"type": "string"},
                        "religion": {"type": "string"},
                        "mythology": {"type": "string"},
                        "historical_notes": {"type": "string"},
                        "cultural_sensitivities": {"type": "array", "items": {"type": "string"}},
                        "source_facts": {"type": "array", "items": {"type": "string"}},
                        "ai_interpretations": {"type": "array", "items": {"type": "string"}},
                        "visualization_choices": {"type": "array", "items": {"type": "string"}},
                    }
                },
            },
            "required": ["title", "summary", "source_language", "acts", "characters", "locations", "events", "themes", "relationships", "cultural_context"]
        }
    
    def _parse_story_result(self, data: Dict[str, Any], language: str) -> StoryGraph:
        """Parse LLM result into StoryGraph."""
        # Convert acts
        acts = [Act(**act) for act in data.get("acts", [])]
        
        # Convert characters
        characters = [CharacterRef(**char) for char in data.get("characters", [])]
        
        # Convert locations
        locations = [LocationRef(**loc) for loc in data.get("locations", [])]
        
        # Convert events
        events = [Event(**evt) for evt in data.get("events", [])]
        
        # Convert themes
        themes = [Theme(**theme) for theme in data.get("themes", [])]
        
        # Convert relationships
        relationships = [Relationship(**rel) for rel in data.get("relationships", [])]
        
        # Convert cultural context
        cultural_context = CulturalContext(**data.get("cultural_context", {}))
        
        # Build timeline from events
        timeline = sorted(events, key=lambda e: e.time)
        
        return StoryGraph(
            title=data.get("title", "Untitled Story"),
            summary=data.get("summary", ""),
            source_language=language,
            acts=acts,
            characters=characters,
            locations=locations,
            events=events,
            themes=themes,
            relationships=relationships,
            timeline=timeline,
            cultural_context=cultural_context,
        )
    
    async def extract_characters(self, project_id: UUID, story_graph: StoryGraph) -> List[CharacterRef]:
        """Extract detailed character information from story graph."""
        # This would use LLM to create detailed character bibles
        # For now, return the character refs from story graph
        return story_graph.characters
    
    def get_story(self, project_id: UUID) -> Optional[StoryGraph]:
        """Get story graph for a project."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        return self.project_manager.load_story(project_dir)
    
    def get_acts(self, project_id: UUID) -> List[Act]:
        """Get all acts for a project."""
        story = self.get_story(project_id)
        return story.acts if story else []
    
    def get_events(self, project_id: UUID) -> List[Event]:
        """Get all events for a project."""
        story = self.get_story(project_id)
        return story.events if story else []
    
    def get_themes(self, project_id: UUID) -> List[Theme]:
        """Get all themes for a project."""
        story = self.get_story(project_id)
        return story.themes if story else []
    
    def get_relationships(self, project_id: UUID) -> List[Relationship]:
        """Get all relationships for a project."""
        story = self.get_story(project_id)
        return story.relationships if story else []
    
    def get_cultural_context(self, project_id: UUID) -> Optional[CulturalContext]:
        """Get cultural context for a project."""
        story = self.get_story(project_id)
        return story.cultural_context if story else None