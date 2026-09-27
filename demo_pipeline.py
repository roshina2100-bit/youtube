#!/usr/bin/env python
"""
Demo script for the Cinematic Multi-Language Video Studio.
Demonstrates the complete YouTube URL to final video pipeline.
"""

import asyncio
import tempfile
import shutil
from pathlib import Path
from uuid import uuid4

# Add backend to path
import sys
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.services.project_manager import ProjectManager
from app.providers.registry import ProviderRegistry
from app.workflow.engine import WorkflowEngine
from app.services.youtube_source_handler import YouTubeSourceHandler
from app.services.pipeline_completion_service import PipelineCompletionService
from app.models.job import Job, JobType, JobStatus
from app.core.config import Settings
from app.models.project import ProjectCreate


async def demo_pipeline():
    """Run a complete demo of the YouTube to final video pipeline."""
    
    print("=" * 80)
    print("Cinematic Multi-Language Video Studio - Pipeline Demo")
    print("=" * 80)
    
    # Create temporary directory for demo
    temp_dir = Path(tempfile.mkdtemp(prefix="cinematic_demo_"))
    print(f"\nDemo directory: {temp_dir}")
    
    try:
        # Create settings
        settings = Settings(
            debug=True,
            test_mode=True,
            project_root=str(temp_dir),
            cors_origins=["http://localhost:4200"],
            max_concurrent_gpu_jobs=1,
            enable_cpu_fallback=True,
            model_idle_timeout=300,
            ai_default_provider="local_python",
            ai_allow_external_provider=True,
            ai_fallback_to_local=False,
            notebooklm={
                "enabled": False,
                "api_key": "",
                "endpoint": "",
                "project_id": "",
                "model": "",
                "timeout_seconds": 300,
                "max_retries": 3,
            },
            models={},
        )
        
        # Initialize services
        print("\n1. Initializing services...")
        project_manager = ProjectManager(str(temp_dir))
        provider_registry = ProviderRegistry()
        await provider_registry.initialize(Settings(
            debug=True,
            test_mode=True,
            project_root=str(temp_dir),
            cors_origins=["http://localhost:4200"],
            max_concurrent_gpu_jobs=1,
            enable_cpu_fallback=True,
            model_idle_timeout=300,
            ai_default_provider="local_python",
            ai_allow_external_provider=True,
            ai_fallback_to_local=False,
            notebooklm={"enabled": False},
            models={},
        ))
        
        workflow_engine = WorkflowEngine(
            project_manager,
            provider_registry
        )
        await workflow_engine.start()
        
        youtube_handler = YouTubeSourceHandler(
            project_manager,
            workflow_engine
        )
        
        pipeline_service = PipelineCompletionService(
            project_manager,
            workflow_engine,
            youtube_handler
        )
        
        print("✓ Services initialized")
        
        # Create project
        print("\n2. Creating project...")
        project_data = ProjectCreate(
            name="Demo Project - YouTube to Video",
            description="Demo project showing YouTube URL to final multilingual video pipeline",
            target_languages=["en", "es", "fr"],
        )
        
        project = project_manager.create_project(project_data)
        project_id = project.project_id
        print(f"✓ Project created: {project.name} (ID: {project_id})")
        
        # Show project structure
        project_dir = project_manager.get_project_path(str(project_id))
        print(f"\nProject directory structure:")
        for item in sorted(project_dir.rglob("*")):
            if item.is_dir():
                rel_path = item.relative_to(temp_dir)
                print(f"  📁 {rel_path}")
        
        # Test YouTube URL validation
        print("\n3. Testing YouTube URL validation...")
        test_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://www.youtube.com/embed/dQw4w9WgXcQ",
            "https://www.youtube.com/shorts/dQw4w9WgXcQ",
            "https://vimeo.com/123456",  # Invalid
        ]
        
        for url in test_urls:
            is_valid = youtube_handler.is_youtube_url(url)
            video_id = youtube_handler.extract_video_id(url) if youtube_handler.is_youtube_url(url) else None
            status = "✓ Valid" if youtube_handler.is_youtube_url(url) else "✗ Invalid"
            print(f"  {status}: {url} -> Video ID: {video_id}")
        
        # Test YouTube import (mock)
        print("\n4. Testing YouTube URL import (mock)...")
        project_id = project_id
        
        # Mock the import
        original_import = youtube_handler.import_youtube_url
        
        async def mock_import(project_id, url, download_video=True, download_transcript=True, quality="best[height<=1080]"):
            project_dir = youtube_handler.project_manager.get_project_path(str(project_id))
            source_dir = project_dir / "source" / "source_media"
            source_dir.mkdir(parents=True, exist_ok=True)
            
            # Create a dummy video file
            dummy_video = source_dir / "demo_video.mp4"
            dummy_video.write_bytes(b"demo video content for testing")
            
            # Create a dummy transcript
            transcript_dir = project_dir / "transcript"
            transcript_dir.mkdir(parents=True, exist_ok=True)
            (transcript_dir / "original.txt").write_text(
                "Welcome to this demo video.\n"
                "This is a demonstration of the Cinematic Multi-Language Video Studio.\n"
                "We can translate this into multiple languages.\n"
                "The pipeline will generate videos in each target language.\n"
                "Thank you for watching!"
            )
            
            return {
                "source_type": "youtube",
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "video_id": "dQw4w9WgXcQ",
                "title": "Demo Video - Cinematic Studio Demo",
                "duration_seconds": 60.0,
                "metadata": {"title": "Demo Video", "duration": 60},
                "video_path": "source/source_media/demo_video.mp4",
                "transcript_path": "transcript/original.txt",
            }
        
        youtube_handler.import_youtube_url = mock_import
        
        try:
            print("  Importing YouTube URL...")
            result = await youtube_handler.import_youtube_url(
                project_id=project_id,
                url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                download_video=True,
                download_transcript=True,
            )
            
            print(f"  ✓ Import successful!")
            print(f"  Title: {result['title']}")
            print(f"  Duration: {result['duration_seconds']}s")
            print(f"  Video: {result.get('video_path', 'N/A')}")
            print(f"  Transcript: {result.get('transcript_path', 'N/A')}")
            
        finally:
            youtube_handler.import_youtube_url = original_import
        
        # Test pipeline stages
        print("\n5. Testing pipeline stages...")
        from app.services.pipeline_completion_service import PipelineStage, STAGE_DEPENDENCIES
        
        print("\nPipeline stages in order:")
        for i, stage in enumerate(PipelineStage):
            deps = [d.value for d in STAGE_DEPENDENCIES.get(stage, [])]
            deps_str = f" (depends on: {', '.join(deps)})" if deps else " (no dependencies)"
            print(f"  {i+1:2d}. {stage.value}{deps_str}")
        
        # Test pipeline service
        print("\n6. Testing pipeline completion service...")
        pipeline_service = PipelineCompletionService(
            project_manager,
            workflow_engine,
            youtube_handler
        )
        
        # Test pipeline state
        state = pipeline_service.get_pipeline_state(project_id)
        print(f"  Pipeline state: {state}")
        
        # Test pipeline stages order
        print("\nPipeline stages in execution order:")
        for i, stage in enumerate(PipelineStage):
            print(f"  {i+1:2d}. {stage.value}")
        
        print("\n" + "=" * 80)
        print("Demo completed successfully!")
        print("=" * 80)
        print("\nNext steps:")
        print("1. Configure real AI models in Settings > Models")
        print("2. Add YouTube API key for real transcript downloading")
        print("3. Configure FFmpeg path if not in system PATH")
        print("4. Run: python -m uvicorn app.main:app --reload (in backend/)")
        print("5. Run: npm start (in frontend/)")
        print("6. Open http://localhost:4200 in browser")
        print("\nProject files are in:", temp_dir)
        
    finally:
        # Cleanup
        print("\nCleaning up...")
        await workflow_engine.stop()
        await provider_registry.shutdown()
        shutil.rmtree(temp_dir, ignore_errors=True)
        print("✓ Cleanup complete")


if __name__ == "__main__":
    asyncio.run(demo_pipeline())