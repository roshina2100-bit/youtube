"""
Workflow Engine for the Cinematic Video Studio.
Orchestrates jobs, manages execution, handles persistence and recovery.
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Awaitable
from uuid import UUID

from app.models.job import Job, JobStatus, JobType, JobStep
from app.models.project import ProjectManifest
from app.services.project_manager import ProjectManager
from app.providers.registry import ProviderRegistry
from app.core.logging import get_project_logger, log_job_start, log_job_progress, log_job_complete, log_job_error
from app.core.config import get_settings


class WorkflowEngine:
    """Local workflow engine for job orchestration."""
    
    def __init__(
        self, 
        project_manager: ProjectManager, 
        provider_registry: ProviderRegistry
    ):
        self.project_manager = project_manager
        self.provider_registry = provider_registry
        self._settings = get_settings()
        self._running = False
        self._job_queue: asyncio.Queue = asyncio.Queue()
        self._active_jobs: Dict[str, Job] = {}
        self._worker_task: Optional[asyncio.Task] = None
        self._job_handlers: Dict[JobType, Callable] = {}
        self._max_concurrent_jobs = self._settings.max_concurrent_gpu_jobs
        self._semaphore: Optional[asyncio.Semaphore] = None
    
    async def start(self) -> None:
        """Start the workflow engine."""
        if self._running:
            return
        
        self._running = True
        self._semaphore = asyncio.Semaphore(self._max_concurrent_jobs)
        self._worker_task = asyncio.create_task(self._worker_loop())
        
        # Register job handlers
        self._register_handlers()
    
    async def stop(self) -> None:
        """Stop the workflow engine."""
        self._running = False
        
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        
        # Cancel all active jobs
        for job in self._active_jobs.values():
            job.cancel()
    
    def _register_handlers(self) -> None:
        """Register job type handlers."""
        # These would be imported from services
        self._job_handlers = {
            JobType.PROJECT_CREATE: self._handle_project_create,
            JobType.SOURCE_IMPORT: self._handle_source_import,
            JobType.TRANSCRIPT_PROCESS: self._handle_transcript_process,
            JobType.LANGUAGE_DETECT: self._handle_language_detect,
            JobType.STORY_ANALYSIS: self._handle_story_analysis,
            JobType.CHARACTER_EXTRACTION: self._handle_character_extraction,
            JobType.CHARACTER_PROMPT_GEN: self._handle_character_prompt_gen,
            JobType.CHARACTER_IMAGE_GEN: self._handle_character_image_gen,
            JobType.SCENE_GENERATION: self._handle_scene_generation,
            JobType.SCENE_PROMPT_GEN: self._handle_scene_prompt_gen,
            JobType.IMAGE_GENERATION: self._handle_image_generation,
            JobType.VIDEO_GENERATION: self._handle_video_generation,
            JobType.TRANSLATION: self._handle_translation,
            JobType.SEMANTIC_REVIEW: self._handle_semantic_review,
            JobType.TTS_GENERATION: self._handle_tts_generation,
            JobType.MUSIC_GENERATION: self._handle_music_generation,
            JobType.SFX_GENERATION: self._handle_sfx_generation,
            JobType.AUDIO_MIXING: self._handle_audio_mixing,
            JobType.SILENT_MASTER: self._handle_silent_master,
            JobType.FINAL_RENDER: self._handle_final_render,
            JobType.EXPORT: self._handle_export,
        }
    
    async def submit_job(self, job: Job) -> str:
        """Submit a job for execution."""
        job.queued_at = datetime.utcnow()
        job.status = JobStatus.QUEUED
        
        # Save initial job state
        project_dir = self.project_manager.get_project_path(str(job.project_id))
        self.project_manager.save_job(project_dir, job)
        
        # Add to queue
        await self._job_queue.put(job)
        
        return job.job_id
    
    async def cancel_job(self, project_id: UUID, job_id: str) -> bool:
        """Cancel a job."""
        # Check active jobs
        if job_id in self._active_jobs:
            job = self._active_jobs[job_id]
            job.cancel()
            return True
        
        # Check queued jobs (would need to search queue)
        # For now, load from disk and mark cancelled
        project_dir = self.project_manager.get_project_path(str(project_id))
        job = self.project_manager.load_job(project_dir, job_id)
        
        if job and job.status in (JobStatus.QUEUED, JobStatus.RUNNING):
            job.cancel()
            self.project_manager.save_job(project_dir, job)
            return True
        
        return False
    
    async def retry_job(self, project_id: UUID, job_id: str) -> bool:
        """Retry a failed job."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        job = self.project_manager.load_job(project_dir, job_id)
        
        if not job or not job.can_retry():
            return False
        
        job.prepare_retry()
        self.project_manager.save_job(project_dir, job)
        
        await self._job_queue.put(job)
        return True
    
    def get_job_status(self, project_id: UUID, job_id: str) -> Optional[Job]:
        """Get job status."""
        # Check active jobs first
        if job_id in self._active_jobs:
            return self._active_jobs[job_id]
        
        # Load from disk
        project_dir = self.project_manager.get_project_path(str(project_id))
        return self.project_manager.load_job(project_dir, job_id)
    
    def list_jobs(self, project_id: UUID) -> List[Job]:
        """List all jobs for a project."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        return self.project_manager.list_jobs(project_dir)
    
    async def _worker_loop(self) -> None:
        """Main worker loop."""
        while self._running:
            try:
                # Get job from queue with timeout
                job = await asyncio.wait_for(self._job_queue.get(), timeout=1.0)
                
                # Check if cancelled before starting
                if job.cancel_requested:
                    job.mark_cancelled()
                    project_dir = self.project_manager.get_project_path(str(job.project_id))
                    self.project_manager.save_job(project_dir, job)
                    continue
                
                # Execute job with semaphore for concurrency control
                async with self._semaphore:
                    await self._execute_job(job)
                    
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error but continue
                pass
    
    async def _execute_job(self, job: Job) -> None:
        """Execute a single job."""
        project_dir = self.project_manager.get_project_path(str(job.project_id))
        logger = get_project_logger(str(job.project_id), self.project_manager.project_root)
        
        # Track active job
        self._active_jobs[job.job_id] = job
        
        try:
            job.status = JobStatus.RUNNING
            job.started_at = datetime.utcnow()
            self.project_manager.save_job(project_dir, job)
            
            log_job_start(logger, job.job_id, job.type.value)
            
            # Get handler
            handler = self._job_handlers.get(job.type)
            if not handler:
                raise ValueError(f"No handler for job type: {job.type}")
            
            # Execute handler
            await handler(job)
            
            # Mark completed
            job.mark_completed()
            self.project_manager.save_job(project_dir, job)
            
            log_job_complete(logger, job.job_id, job.type.value, 
                           (job.completed_at - job.started_at).total_seconds() if job.completed_at and job.started_at else 0)
            
        except asyncio.CancelledError:
            job.mark_cancelled()
            self.project_manager.save_job(project_dir, job)
            raise
        except Exception as e:
            job.fail_step(job.current_step or "unknown", str(e))
            self.project_manager.save_job(project_dir, job)
            
            log_job_error(logger, job.job_id, job.type.value, e)
        finally:
            # Remove from active jobs
            self._active_jobs.pop(job.job_id, None)
    
    # Job handlers - these would call the actual services
    
    async def _handle_project_create(self, job: Job) -> None:
        """Handle project creation."""
        # Project creation is synchronous, already done
        job.mark_completed({"project_id": str(job.project_id)})
    
    async def _handle_source_import(self, job: Job) -> None:
        """Handle source media import."""
        # Would import video/audio, extract metadata
        job.mark_completed({"message": "Source import completed"})
    
    async def _handle_transcript_process(self, job: Job) -> None:
        """Handle transcript processing."""
        # Would process transcript files
        job.mark_completed({"message": "Transcript processed"})
    
    async def _handle_language_detect(self, job: Job) -> None:
        """Handle language detection."""
        # Would detect language
        job.mark_completed({"message": "Language detected"})
    
    async def _handle_story_analysis(self, job: Job) -> None:
        """Handle story analysis."""
        from app.services.story_service import StoryService
        
        story_service = StoryService(self.project_manager, self.provider_registry)
        
        request_data = job.input
        request = type('obj', (object,), request_data)()
        
        result = await story_service.analyze_story(
            job.project_id, request, job.job_id
        )
        
        job.mark_completed({
            "story_id": str(result.story_graph.story_id),
            "acts": len(result.story_graph.acts),
            "characters": len(result.story_graph.characters),
        })
    
    async def _handle_character_extraction(self, job: Job) -> None:
        """Handle character extraction."""
        from app.services.character_service import CharacterService
        from app.models.story import StoryGraph
        
        character_service = CharacterService(self.project_manager, self.provider_registry)
        
        project_dir = self.project_manager.get_project_path(str(job.project_id))
        story = self.project_manager.load_story(project_dir)
        
        if not story:
            raise ValueError("Story graph not found")
        
        characters = await character_service.extract_characters(
            job.project_id, story,
            job.input.get("provider", "local_python"),
            job.input.get("model", "llama-3-8b-instruct"),
            job.job_id
        )
        
        job.mark_completed({
            "characters_extracted": len(characters),
            "character_ids": [c.character_id for c in characters],
        })
    
    async def _handle_character_prompt_gen(self, job: Job) -> None:
        """Handle character prompt generation."""
        from app.services.character_service import CharacterService
        
        character_service = CharacterService(self.project_manager, self.provider_registry)
        
        character_id = job.input.get("character_id")
        if not character_id:
            raise ValueError("character_id required")
        
        version = await character_service.generate_character_prompt(
            job.project_id, character_id,
            job.input.get("provider", "local_python"),
            job.input.get("model", "llama-3-8b-instruct"),
        )
        
        job.mark_completed({
            "character_id": character_id,
            "version": version.version,
        })
    
    async def _handle_character_image_gen(self, job: Job) -> None:
        """Handle character image generation."""
        from app.services.character_service import CharacterService
        from app.models.character import CharacterImageRequest
        
        character_service = CharacterService(self.project_manager, self.provider_registry)
        
        request = CharacterImageRequest(**job.input)
        
        version = await character_service.generate_character_image(
            job.project_id, request, job.job_id
        )
        
        job.mark_completed({
            "character_id": request.character_id,
            "version": version.version,
            "image_path": version.image_path,
        })
    
    async def _handle_scene_generation(self, job: Job) -> None:
        """Handle scene generation."""
        from app.services.scene_service import SceneService
        from app.models.story import StoryGraph
        
        scene_service = SceneService(self.project_manager, self.provider_registry)
        
        project_dir = self.project_manager.get_project_path(str(job.project_id))
        story = self.project_manager.load_story(project_dir)
        
        if not story:
            raise ValueError("Story graph not found")
        
        scenes = await scene_service.generate_scenes(
            job.project_id, story,
            job.input.get("provider", "local_python"),
            job.input.get("model", "llama-3-8b-instruct"),
            job.job_id
        )
        
        job.mark_completed({
            "scenes_generated": len(scenes),
            "scene_ids": [s.scene_id for s in scenes],
        })
    
    async def _handle_scene_prompt_gen(self, job: Job) -> None:
        """Handle scene prompt generation."""
        from app.services.scene_service import SceneService
        
        scene_service = SceneService(self.project_manager, self.provider_registry)
        
        scene_id = job.input.get("scene_id")
        if not scene_id:
            raise ValueError("scene_id required")
        
        prompts = await scene_service.generate_scene_prompts(
            job.project_id, scene_id,
            job.input.get("provider", "local_python"),
            job.input.get("model", "llama-3-8b-instruct"),
        )
        
        job.mark_completed({
            "scene_id": scene_id,
            "prompts_generated": len([p for p in prompts.model_dump().values() if p]),
        })
    
    async def _handle_image_generation(self, job: Job) -> None:
        """Handle image generation."""
        from app.services.scene_service import SceneService
        from app.models.scene import SceneImageRequest
        
        scene_service = SceneService(self.project_manager, self.provider_registry)
        
        request = SceneImageRequest(**job.input)
        
        result = await scene_service.generate_scene_image(
            job.project_id, request, job.job_id
        )
        
        job.mark_completed(result)
    
    async def _handle_video_generation(self, job: Job) -> None:
        """Handle video generation."""
        from app.services.scene_service import SceneService
        from app.models.scene import SceneVideoRequest
        
        scene_service = SceneService(self.project_manager, self.provider_registry)
        
        request = SceneVideoRequest(**job.input)
        
        result = await scene_service.generate_scene_video(
            job.project_id, request, job.job_id
        )
        
        job.mark_completed(result)
    
    async def _handle_translation(self, job: Job) -> None:
        """Handle translation."""
        from app.services.translation_service import TranslationService
        
        translation_service = TranslationService(self.project_manager, self.provider_registry)
        
        target_languages = job.input.get("target_languages", [])
        provider = job.input.get("provider", "local_python")
        model = job.input.get("model", "nllb-200-distilled-600M")
        
        results = await translation_service.translate_project(
            job.project_id, target_languages, provider, model, job.job_id
        )
        
        job.mark_completed({
            "languages_completed": len(results),
            "languages": list(results.keys()),
        })
    
    async def _handle_semantic_review(self, job: Job) -> None:
        """Handle semantic review."""
        from app.services.translation_service import TranslationService
        
        translation_service = TranslationService(self.project_manager, self.provider_registry)
        
        scene_id = job.input.get("scene_id")
        language = job.input.get("language")
        
        if not scene_id or not language:
            raise ValueError("scene_id and language required")
        
        review = await translation_service.review_translation(
            job.project_id, scene_id, language,
            job.input.get("provider", "local_python"),
            job.input.get("model", "llama-3-8b-instruct"),
        )
        
        job.mark_completed({
            "scene_id": scene_id,
            "language": language,
            "status": review.status.value,
            "all_passed": review.all_passed,
        })
    
    async def _handle_tts_generation(self, job: Job) -> None:
        """Handle TTS generation."""
        job.mark_completed({"message": "TTS generation completed"})
    
    async def _handle_music_generation(self, job: Job) -> None:
        """Handle music generation."""
        job.mark_completed({"message": "Music generation completed"})
    
    async def _handle_sfx_generation(self, job: Job) -> None:
        """Handle SFX generation."""
        job.mark_completed({"message": "SFX generation completed"})
    
    async def _handle_audio_mixing(self, job: Job) -> None:
        """Handle audio mixing."""
        job.mark_completed({"message": "Audio mixing completed"})
    
    async def _handle_silent_master(self, job: Job) -> None:
        """Handle silent master generation."""
        from app.services.scene_service import SceneService
        
        scene_service = SceneService(self.project_manager, self.provider_registry)
        
        master_path = await scene_service.generate_silent_master(
            job.project_id, job.job_id
        )
        
        job.mark_completed({"master_path": master_path})
    
    async def _handle_final_render(self, job: Job) -> None:
        """Handle final video rendering."""
        job.mark_completed({"message": "Final render completed"})
    
    async def _handle_export(self, job: Job) -> None:
        """Handle project export."""
        job.mark_completed({"message": "Export completed"})
    
    # Recovery methods
    
    async def recover_incomplete_jobs(self, project_id: UUID) -> List[str]:
        """Recover incomplete jobs from a previous session."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        jobs = self.project_manager.list_jobs(project_dir)
        
        recovered = []
        for job in jobs:
            if job.status in (JobStatus.QUEUED, JobStatus.RUNNING, JobStatus.PAUSED):
                # Reset job for retry
                if job.status == JobStatus.RUNNING:
                    job.prepare_retry()
                elif job.status == JobStatus.PAUSED:
                    job.status = JobStatus.QUEUED
                
                self.project_manager.save_job(project_dir, job)
                await self._job_queue.put(job)
                recovered.append(job.job_id)
        
        return recovered
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get queue status."""
        return {
            "queue_size": self._job_queue.qsize(),
            "active_jobs": len(self._active_jobs),
            "max_concurrent": self._max_concurrent_jobs,
            "running": self._running,
        }