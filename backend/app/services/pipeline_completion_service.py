"""
Pipeline Completion Service for the Cinematic Video Studio.
Monitors workflow execution and ensures pipeline completes from start to end.
"""

import asyncio
from typing import Optional, Dict, Any, List, Callable
from uuid import UUID
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field

from app.services.project_manager import ProjectManager
from app.workflow.engine import WorkflowEngine
from app.models.job import Job, JobType, JobStatus
from app.services.youtube_source_handler import YouTubeSourceHandler
from app.core.config import get_settings
from app.core.logging import get_project_logger


class PipelineStage(str, Enum):
    """Pipeline stages in order."""
    SOURCE_IMPORT = "source_import"
    TRANSCRIPT_PROCESS = "transcript_process"
    LANGUAGE_DETECT = "language_detect"
    STORY_ANALYSIS = "story_analysis"
    CHARACTER_EXTRACTION = "character_extraction"
    CHARACTER_PROMPT_GEN = "character_prompt_gen"
    CHARACTER_IMAGE_GEN = "character_image_gen"
    CHARACTER_APPROVAL = "character_approval"
    SCENE_GENERATION = "scene_generation"
    SCENE_PROMPT_GEN = "scene_prompt_gen"
    IMAGE_GENERATION = "image_generation"
    VIDEO_GENERATION = "video_generation"
    TRANSLATION = "translation"
    SEMANTIC_REVIEW = "semantic_review"
    TTS_GENERATION = "tts_generation"
    MUSIC_GENERATION = "music_generation"
    SFX_GENERATION = "sfx_generation"
    AUDIO_MIXING = "audio_mixing"
    SILENT_MASTER = "silent_master"
    FINAL_RENDER = "final_render"
    EXPORT = "export"


# Pipeline stage order
PIPELINE_STAGES = [
    PipelineStage.SOURCE_IMPORT,
    PipelineStage.TRANSCRIPT_PROCESS,
    PipelineStage.LANGUAGE_DETECT,
    PipelineStage.STORY_ANALYSIS,
    PipelineStage.CHARACTER_EXTRACTION,
    PipelineStage.CHARACTER_PROMPT_GEN,
    PipelineStage.CHARACTER_IMAGE_GEN,
    PipelineStage.CHARACTER_APPROVAL,
    PipelineStage.SCENE_GENERATION,
    PipelineStage.SCENE_PROMPT_GEN,
    PipelineStage.IMAGE_GENERATION,
    PipelineStage.VIDEO_GENERATION,
    PipelineStage.TRANSLATION,
    PipelineStage.SEMANTIC_REVIEW,
    PipelineStage.TTS_GENERATION,
    PipelineStage.MUSIC_GENERATION,
    PipelineStage.SFX_GENERATION,
    PipelineStage.AUDIO_MIXING,
    PipelineStage.SILENT_MASTER,
    PipelineStage.FINAL_RENDER,
    PipelineStage.EXPORT,
]

# Stage dependencies (which stages must complete before this one)
STAGE_DEPENDENCIES = {
    PipelineStage.TRANSCRIPT_PROCESS: [PipelineStage.SOURCE_IMPORT],
    PipelineStage.LANGUAGE_DETECT: [PipelineStage.TRANSCRIPT_PROCESS],
    PipelineStage.STORY_ANALYSIS: [PipelineStage.TRANSCRIPT_PROCESS, PipelineStage.LANGUAGE_DETECT],
    PipelineStage.CHARACTER_EXTRACTION: [PipelineStage.STORY_ANALYSIS],
    PipelineStage.CHARACTER_PROMPT_GEN: [PipelineStage.CHARACTER_EXTRACTION],
    PipelineStage.CHARACTER_IMAGE_GEN: [PipelineStage.CHARACTER_PROMPT_GEN],
    PipelineStage.CHARACTER_APPROVAL: [PipelineStage.CHARACTER_IMAGE_GEN],
    PipelineStage.SCENE_GENERATION: [PipelineStage.STORY_ANALYSIS, PipelineStage.CHARACTER_EXTRACTION],
    PipelineStage.SCENE_PROMPT_GEN: [PipelineStage.SCENE_GENERATION],
    PipelineStage.IMAGE_GENERATION: [PipelineStage.SCENE_PROMPT_GEN, PipelineStage.CHARACTER_APPROVAL],
    PipelineStage.VIDEO_GENERATION: [PipelineStage.IMAGE_GENERATION],
    PipelineStage.TRANSLATION: [PipelineStage.SCENE_GENERATION, PipelineStage.SCENE_PROMPT_GEN],
    PipelineStage.SEMANTIC_REVIEW: [PipelineStage.TRANSLATION],
    PipelineStage.TTS_GENERATION: [PipelineStage.TRANSLATION, PipelineStage.SEMANTIC_REVIEW],
    PipelineStage.MUSIC_GENERATION: [PipelineStage.TRANSLATION],
    PipelineStage.SFX_GENERATION: [PipelineStage.TRANSLATION],
    PipelineStage.AUDIO_MIXING: [PipelineStage.TTS_GENERATION, PipelineStage.MUSIC_GENERATION, PipelineStage.SFX_GENERATION],
    PipelineStage.SILENT_MASTER: [PipelineStage.VIDEO_GENERATION],
    PipelineStage.FINAL_RENDER: [PipelineStage.SILENT_MASTER, PipelineStage.AUDIO_MIXING],
    PipelineStage.EXPORT: [PipelineStage.FINAL_RENDER],
}


@dataclass
class PipelineState:
    """State of the pipeline for a project."""
    project_id: UUID
    current_stage: Optional[PipelineStage] = None
    completed_stages: List[PipelineStage] = field(default_factory=list)
    failed_stages: List[PipelineStage] = field(default_factory=list)
    stage_results: Dict[PipelineStage, Dict[str, Any]] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    auto_continue: bool = True
    target_languages: List[str] = field(default_factory=list)
    providers: Dict[str, str] = field(default_factory=dict)


class PipelineCompletionService:
    """Service to monitor and ensure pipeline completion."""
    
    def __init__(
        self,
        project_manager: ProjectManager,
        workflow_engine: WorkflowEngine,
        youtube_handler: YouTubeSourceHandler,
    ):
        self.project_manager = project_manager
        self.workflow_engine = workflow_engine
        self.youtube_handler = youtube_handler
        self._settings = get_settings()
        self._pipeline_states: Dict[UUID, PipelineState] = {}
        self._monitoring_tasks: Dict[UUID, asyncio.Task] = {}
        self._stage_handlers: Dict[PipelineStage, Callable] = {}
        self._callbacks: Dict[UUID, List[Callable]] = {}
    
    def register_stage_handler(self, stage: PipelineStage, handler: Callable) -> None:
        """Register a handler for a pipeline stage."""
        self._stage_handlers[stage] = handler
    
    def register_callback(self, project_id: UUID, callback: Callable) -> None:
        """Register a callback for pipeline events."""
        if project_id not in self._callbacks:
            self._callbacks[project_id] = []
        self._callbacks[project_id].append(callback)
    
    async def start_pipeline(
        self,
        project_id: UUID,
        source_url: str,
        target_languages: List[str] = None,
        providers: Dict[str, str] = None,
        auto_continue: bool = True,
    ) -> PipelineState:
        """Start the complete pipeline from a YouTube URL."""
        # Initialize pipeline state
        state = PipelineState(
            project_id=project_id,
            target_languages=target_languages or [],
            providers=providers or {},
            auto_continue=auto_continue,
            started_at=datetime.utcnow(),
        )
        self._pipeline_states[project_id] = state
        
        # Start monitoring
        self._monitoring_tasks[project_id] = asyncio.create_task(
            self._monitor_pipeline(project_id)
        )
        
        # Start with source import
        await self._execute_stage(project_id, PipelineStage.SOURCE_IMPORT, {
            "url": source_url,
        })
        
        return state
    
    async def _monitor_pipeline(self, project_id: UUID) -> None:
        """Monitor pipeline execution and auto-continue."""
        state = self._pipeline_states.get(project_id)
        if not state:
            return
        
        while True:
            await asyncio.sleep(5)  # Check every 5 seconds
            
            # Check if pipeline is complete
            if self._is_pipeline_complete(state):
                state.completed_at = datetime.utcnow()
                await self._notify_completion(project_id, state)
                break
            
            # Check for failed stages
            if state.failed_stages and not state.auto_continue:
                state.error = f"Pipeline stopped due to failed stages: {[s.value for s in state.failed_stages]}"
                await self._notify_failure(project_id, state)
                break
            
            # Auto-continue to next stage if current is complete
            if state.auto_continue and state.current_stage:
                next_stage = self._get_next_stage(state)
                if next_stage and self._can_execute_stage(state, next_stage):
                    await self._execute_stage(project_id, next_stage, {})
            
            # Check for timeout
            if state.started_at:
                elapsed = (datetime.utcnow() - state.started_at).total_seconds()
                if elapsed > self._settings.pipeline_timeout_seconds:
                    state.error = "Pipeline timeout"
                    await self._notify_failure(project_id, state)
                    break
    
    def _is_pipeline_complete(self, state: PipelineState) -> bool:
        """Check if all pipeline stages are complete."""
        return len(state.completed_stages) == len(PIPELINE_STAGES)
    
    def _get_next_stage(self, state: PipelineState) -> Optional[PipelineStage]:
        """Get the next stage to execute."""
        for stage in PIPELINE_STAGES:
            if stage not in state.completed_stages and stage not in state.failed_stages:
                return stage
        return None
    
    def _can_execute_stage(self, state: PipelineState, stage: PipelineStage) -> bool:
        """Check if a stage can be executed (dependencies met)."""
        dependencies = STAGE_DEPENDENCIES.get(stage, [])
        return all(dep in state.completed_stages for dep in dependencies)
    
    async def _execute_stage(self, project_id: UUID, stage: PipelineStage, input_data: Dict[str, Any]) -> None:
        """Execute a pipeline stage."""
        state = self._pipeline_states.get(project_id)
        if not state:
            return
        
        state.current_stage = stage
        
        # Get handler for this stage
        handler = self._stage_handlers.get(stage)
        if not handler:
            # Use default workflow engine job submission
            await self._submit_default_job(project_id, stage)
        else:
            try:
                result = await handler(project_id, self._get_stage_input(state, stage))
                state.stage_results[stage] = result
                state.completed_stages.append(stage)
                await self._notify_stage_complete(project_id, stage, result)
            except Exception as e:
                state.failed_stages.append(stage)
                state.error = f"Stage {stage.value} failed: {str(e)}"
                await self._notify_stage_failed(project_id, stage, str(e))
    
    def _get_stage_input(self, state: PipelineState, stage: PipelineStage) -> Dict[str, Any]:
        """Get input data for a stage based on previous results."""
        base_input = {
            "project_id": state.project_id,
            "target_languages": state.target_languages,
            "providers": state.providers,
        }
        
        # Add stage-specific inputs from previous results
        if stage == PipelineStage.TRANSLATION:
            base_input["target_languages"] = state.target_languages
        elif stage in [PipelineStage.TTS_GENERATION, PipelineStage.MUSIC_GENERATION, PipelineStage.SFX_GENERATION]:
            base_input["target_languages"] = state.target_languages
        
        return base_input
    
    async def _submit_default_job(self, project_id: UUID, stage: PipelineStage) -> None:
        """Submit a default job for a stage."""
        stage_to_job_type = {
            PipelineStage.SOURCE_IMPORT: JobType.SOURCE_IMPORT,
            PipelineStage.TRANSCRIPT_PROCESS: JobType.TRANSCRIPT_PROCESS,
            PipelineStage.LANGUAGE_DETECT: JobType.LANGUAGE_DETECT,
            PipelineStage.STORY_ANALYSIS: JobType.STORY_ANALYSIS,
            PipelineStage.CHARACTER_EXTRACTION: JobType.CHARACTER_EXTRACTION,
            PipelineStage.CHARACTER_PROMPT_GEN: JobType.CHARACTER_PROMPT_GEN,
            PipelineStage.CHARACTER_IMAGE_GEN: JobType.CHARACTER_IMAGE_GEN,
            PipelineStage.SCENE_GENERATION: JobType.SCENE_GENERATION,
            PipelineStage.SCENE_PROMPT_GEN: JobType.SCENE_PROMPT_GEN,
            PipelineStage.IMAGE_GENERATION: JobType.IMAGE_GENERATION,
            PipelineStage.VIDEO_GENERATION: JobType.VIDEO_GENERATION,
            PipelineStage.TRANSLATION: JobType.TRANSLATION,
            PipelineStage.SEMANTIC_REVIEW: JobType.SEMANTIC_REVIEW,
            PipelineStage.TTS_GENERATION: JobType.TTS_GENERATION,
            PipelineStage.MUSIC_GENERATION: JobType.MUSIC_GENERATION,
            PipelineStage.SFX_GENERATION: JobType.SFX_GENERATION,
            PipelineStage.AUDIO_MIXING: JobType.AUDIO_MIXING,
            PipelineStage.SILENT_MASTER: JobType.SILENT_MASTER,
            PipelineStage.FINAL_RENDER: JobType.FINAL_RENDER,
            PipelineStage.EXPORT: JobType.EXPORT,
        }
        
        job_type = stage_to_job_type.get(stage)
        if job_type:
            job = Job(
                project_id=project_id,
                type=job_type,
                input={},
            )
            await self.workflow_engine.submit_job(job)
    
    async def _notify_stage_complete(self, project_id: UUID, stage: PipelineStage, result: Dict[str, Any]) -> None:
        """Notify callbacks of stage completion."""
        for callback in self._callbacks.get(project_id, []):
            try:
                await callback("stage_complete", {"stage": stage.value, "result": result})
            except Exception:
                pass
    
    async def _notify_stage_failed(self, project_id: UUID, stage: PipelineStage, error: str) -> None:
        """Notify callbacks of stage failure."""
        for callback in self._callbacks.get(project_id, []):
            try:
                await callback("stage_failed", {"stage": stage.value, "error": error})
            except Exception:
                pass
    
    async def _notify_completion(self, project_id: UUID, state: PipelineState) -> None:
        """Notify callbacks of pipeline completion."""
        for callback in self._callbacks.get(project_id, []):
            try:
                await callback("pipeline_complete", {"state": state})
            except Exception:
                pass
    
    async def _notify_failure(self, project_id: UUID, state: PipelineState) -> None:
        """Notify callbacks of pipeline failure."""
        for callback in self._callbacks.get(project_id, []):
            try:
                await callback("pipeline_failed", {"state": state, "error": state.error})
            except Exception:
                pass
    
    def get_pipeline_state(self, project_id: UUID) -> Optional[PipelineState]:
        """Get current pipeline state."""
        return self._pipeline_states.get(project_id)
    
    def stop_pipeline(self, project_id: UUID) -> bool:
        """Stop pipeline monitoring."""
        if project_id in self._monitoring_tasks:
            self._monitoring_tasks[project_id].cancel()
            del self._monitoring_tasks[project_id]
            return True
        return False
    
    def pause_pipeline(self, project_id: UUID) -> bool:
        """Pause auto-continue."""
        state = self._pipeline_states.get(project_id)
        if state:
            state.auto_continue = False
            return True
        return False
    
    def resume_pipeline(self, project_id: UUID) -> bool:
        """Resume auto-continue."""
        state = self._pipeline_states.get(project_id)
        if state:
            state.auto_continue = True
            return True
        return False
    
    def retry_failed_stage(self, project_id: UUID, stage: PipelineStage) -> bool:
        """Retry a failed stage."""
        state = self._pipeline_states.get(project_id)
        if state and stage in state.failed_stages:
            state.failed_stages.remove(stage)
            asyncio.create_task(self._execute_stage(project_id, stage, {}))
            return True
        return False


# Global pipeline completion service instance
_pipeline_completion_service: Optional[PipelineCompletionService] = None


def get_pipeline_completion_service() -> PipelineCompletionService:
    """Get the global pipeline completion service instance."""
    global _pipeline_completion_service
    if _pipeline_completion_service is None:
        from app.main import app
        _pipeline_completion_service = PipelineCompletionService(
            app.state.project_manager,
            app.state.workflow_engine,
            app.state.youtube_handler,
        )
    return _pipeline_completion_service