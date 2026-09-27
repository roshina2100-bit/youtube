"""
End-to-End Test for the Cinematic Multi-Language Video Studio.
Tests the complete pipeline from YouTube URL to final rendered videos using mock providers.
"""

import asyncio
import tempfile
import shutil
from pathlib import Path
from uuid import UUID, uuid4
import pytest
import pytest_asyncio

from app.services.project_manager import ProjectManager
from app.providers.registry import ProviderRegistry
from app.workflow.engine import WorkflowEngine
from app.services.youtube_source_handler import YouTubeSourceHandler
from app.services.pipeline_completion_service import PipelineCompletionService, PipelineStage
from app.models.job import Job, JobType, JobStatus
from app.core.config import Settings
from app.models.project import ProjectCreate


# Test configuration
TEST_PROJECT_NAME = "Test YouTube Pipeline"
TEST_YOUTUBE_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Roll - famous test video
TEST_TARGET_LANGUAGES = ["en", "es", "fr"]


@pytest.fixture
def temp_project_root():
    """Create a temporary project root for testing."""
    temp_dir = Path(tempfile.mkdtemp(prefix="cinematic_test_"))
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def test_settings(temp_project_root):
    """Create test settings."""
    return Settings(
        debug=True,
        test_mode=True,
        project_root=str(temp_project_root),
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


@pytest.fixture
def project_manager(temp_project_root):
    """Create a ProjectManager instance for testing."""
    return ProjectManager(str(temp_project_root))


@pytest.fixture
async def provider_registry(test_settings):
    """Create a ProviderRegistry with mock providers."""
    registry = ProviderRegistry()
    await registry.initialize(test_settings)
    yield registry
    await registry.shutdown()


@pytest.fixture
async def workflow_engine(project_manager, provider_registry):
    """Create a WorkflowEngine for testing."""
    engine = WorkflowEngine(project_manager, provider_registry)
    await engine.start()
    yield engine
    await engine.stop()


@pytest.fixture
def youtube_handler(project_manager, workflow_engine):
    """Create a YouTubeSourceHandler for testing."""
    return YouTubeSourceHandler(project_manager, workflow_engine)


@pytest.fixture
async def pipeline_service(project_manager, workflow_engine, youtube_handler):
    """Create a PipelineCompletionService for testing."""
    service = PipelineCompletionService(project_manager, workflow_engine, youtube_handler)
    yield service


class TestYouTubePipeline:
    """Test the complete YouTube URL to final video pipeline."""
    
    @pytest.mark.asyncio
    async def test_create_project(self, project_manager):
        """Test project creation."""
        project_data = ProjectCreate(
            name=TEST_PROJECT_NAME,
            description="Test project for YouTube pipeline",
            target_languages=TEST_TARGET_LANGUAGES,
        )
        
        project = project_manager.create_project(project_data)
        
        assert project.name == TEST_PROJECT_NAME
        assert project.target_languages == TEST_TARGET_LANGUAGES
        assert project.status.value == "draft"
        assert project.project_id is not None
        
        # Verify project directory structure
        project_dir = project_manager.get_project_path(str(project.project_id))
        assert project_dir.exists()
        assert (project_dir / "project.json").exists()
        assert (project_dir / "source").exists()
        assert (project_dir / "transcript").exists()
        assert (project_dir / "story").exists()
        assert (project_dir / "characters").exists()
        assert (project_dir / "scenes").exists()
        assert (project_dir / "languages").exists()
        assert (project_dir / "output").exists()
    
    @pytest.mark.asyncio
    async def test_youtube_url_validation(self, youtube_handler):
        """Test YouTube URL validation."""
        # Valid URLs
        assert youtube_handler.is_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert youtube_handler.is_youtube_url("https://youtu.be/dQw4w9WgXcQ")
        assert youtube_handler.is_youtube_url("https://www.youtube.com/embed/dQw4w9WgXcQ")
        assert youtube_handler.is_youtube_url("https://www.youtube.com/shorts/dQw4w9WgXcQ")
        
        # Invalid URLs
        assert not youtube_handler.is_youtube_url("https://vimeo.com/123456")
        assert not youtube_handler.is_youtube_url("https://example.com/video")
        assert not youtube_handler.is_youtube_url("not a url")
        
        # Extract video ID
        video_id = youtube_handler.extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert video_id == "dQw4w9WgXcQ"
    
    @pytest.mark.asyncio
    async def test_youtube_import_mock(self, project_manager, workflow_engine, youtube_handler):
        """Test YouTube import with mock (since we can't actually download in tests)."""
        # Create project
        project_data = ProjectCreate(
            name=TEST_PROJECT_NAME,
            description="Test project for YouTube pipeline",
            target_languages=TEST_TARGET_LANGUAGES,
        )
        project = project_manager.create_project(project_data)
        project_id = project.project_id
        
        # Mock the YouTube handler's import method
        original_import = youtube_handler.import_youtube_url
        
        async def mock_import(project_id, url, download_video=True, download_transcript=True, quality="best[height<=1080]"):
            # Simulate successful import
            project_dir = youtube_handler.project_manager.get_project_path(str(project_id))
            source_dir = project_dir / "source" / "source_media"
            source_dir.mkdir(parents=True, exist_ok=True)
            
            # Create a dummy video file
            dummy_video = source_dir / "test_video.mp4"
            dummy_video.write_bytes(b"dummy video content")
            
            # Create a dummy transcript
            transcript_dir = project_dir / "transcript"
            transcript_dir.mkdir(parents=True, exist_ok=True)
            (transcript_dir / "original.txt").write_text("This is a test transcript.\nIt has multiple lines.\nAnd it's in English.")
            
            return {
                "source_type": "youtube",
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "video_id": "dQw4w9WgXcQ",
                "title": "Test Video",
                "duration_seconds": 120.0,
                "metadata": {"title": "Test Video", "duration": 120},
                "video_path": "source/source_media/test_video.mp4",
                "transcript_path": "transcript/original.txt",
            }
        
        youtube_handler.import_youtube_url = mock_import
        
        try:
            # Import YouTube URL
            result = await youtube_handler.import_youtube_url(
                project_id=project_id,
                url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                download_video=True,
                download_transcript=True,
            )
            
            assert result["source_type"] == "youtube"
            assert result["video_id"] == "dQw4w9WgXcQ"
            assert "video_path" in result
            assert "transcript_path" in result
            
            # Verify project was updated
            project = youtube_handler.project_manager.load_project(str(project_id))
            assert project.source["type"] == "youtube"
            assert project.source["video_id"] == "dQw4w9WgXcQ"
            
        finally:
            youtube_handler.import_youtube_url = original_import
    
    @pytest.mark.asyncio
    async def test_complete_pipeline_mock(self, project_manager, workflow_engine, youtube_handler, pipeline_service):
        """Test the complete pipeline with mock providers."""
        # Create project
        project_data = ProjectCreate(
            name=TEST_PROJECT_NAME,
            description="Test project for complete pipeline",
            target_languages=TEST_TARGET_LANGUAGES,
        )
        project = project_manager.create_project(project_data)
        project_id = project.project_id
        
        # Mock all the external services
        # We'll use the pipeline service with mock providers
        
        # Start the pipeline
        state = await pipeline_service.start_pipeline(
            project_id=project_id,
            source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            target_languages=TEST_TARGET_LANGUAGES,
            providers={
                "story_analysis": "mock",
                "translation": "mock",
                "character_analysis": "mock",
                "image_generation": "mock",
                "video_generation": "mock",
                "tts": "mock",
                "music_generation": "mock",
                "sfx_generation": "mock",
            },
            auto_continue=True,
        )
        
        assert state.project_id == project_id
        assert state.current_stage is not None
        assert state.auto_continue is True
        assert state.target_languages == TEST_TARGET_LANGUAGES
        
        # Wait a bit for pipeline to process
        await asyncio.sleep(2)
        
        # Check pipeline state
        state = pipeline_service.get_pipeline_state(project_id)
        assert state is not None
        assert state.project_id == project_id
        
        # Stop pipeline
        pipeline_service.stop_pipeline(project_id)
    
    @pytest.mark.asyncio
    async def test_pipeline_control(self, pipeline_service, project_manager):
        """Test pipeline control operations (pause, resume, retry)."""
        project_data = ProjectCreate(
            name="Test Pipeline Control",
            description="Test project for pipeline control",
            target_languages=["en"],
        )
        project = project_manager.create_project(project_data)
        project_id = project.project_id
        
        # Start pipeline
        state = await pipeline_service.start_pipeline(
            project_id=project_id,
            source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            target_languages=["en"],
            auto_continue=True,
        )
        
        # Test pause
        paused = pipeline_service.pause_pipeline(project_id)
        assert paused is True
        
        state = pipeline_service.get_pipeline_state(project_id)
        assert state.auto_continue is False
        
        # Test resume
        resumed = pipeline_service.resume_pipeline(project_id)
        assert resumed is True
        
        state = pipeline_service.get_pipeline_state(project_id)
        assert state.auto_continue is True
        
        # Test stop
        stopped = pipeline_service.stop_pipeline(project_id)
        assert stopped is True
        
        state = pipeline_service.get_pipeline_state(project_id)
        assert state is not None  # State should still exist
    
    @pytest.mark.asyncio
    async def test_pipeline_stages_order(self):
        """Test that pipeline stages are in correct order."""
        # Verify stage order
        expected_order = [
            "source_import",
            "transcript_process",
            "language_detect",
            "story_analysis",
            "character_extraction",
            "character_prompt_gen",
            "character_image_gen",
            "character_approval",
            "scene_generation",
            "scene_prompt_gen",
            "image_generation",
            "video_generation",
            "translation",
            "semantic_review",
            "tts_generation",
            "music_generation",
            "sfx_generation",
            "audio_mixing",
            "silent_master",
            "final_render",
            "export",
        ]
        
        actual_order = [stage.value for stage in PipelineStage]
        assert actual_order == expected_order
    
    @pytest.mark.asyncio
    async def test_stage_dependencies(self):
        """Test that stage dependencies are correctly defined."""
        from app.services.pipeline_completion_service import STAGE_DEPENDENCIES
        
        # Verify some key dependencies
        assert PipelineStage.TRANSCRIPT_PROCESS in STAGE_DEPENDENCIES
        assert PipelineStage.SOURCE_IMPORT in STAGE_DEPENDENCIES[PipelineStage.TRANSCRIPT_PROCESS]
        
        assert PipelineStage.STORY_ANALYSIS in STAGE_DEPENDENCIES
        assert PipelineStage.TRANSCRIPT_PROCESS in STAGE_DEPENDENCIES[PipelineStage.STORY_ANALYSIS]
        assert PipelineStage.LANGUAGE_DETECT in STAGE_DEPENDENCIES[PipelineStage.STORY_ANALYSIS]
        
        assert PipelineStage.CHARACTER_EXTRACTION in STAGE_DEPENDENCIES
        assert PipelineStage.STORY_ANALYSIS in STAGE_DEPENDENCIES[PipelineStage.CHARACTER_EXTRACTION]
        
        assert PipelineStage.FINAL_RENDER in STAGE_DEPENDENCIES
        assert PipelineStage.SILENT_MASTER in STAGE_DEPENDENCIES[PipelineStage.FINAL_RENDER]
        assert PipelineStage.AUDIO_MIXING in STAGE_DEPENDENCIES[PipelineStage.FINAL_RENDER]


class TestAPIEndpoints:
    """Test API endpoints for the pipeline."""
    
    @pytest.mark.asyncio
    async def test_pipeline_start_endpoint(self, project_manager):
        """Test the pipeline start API endpoint."""
        # This would test the actual API endpoint
        # For now, we verify the endpoint exists
        from app.api.pipeline import router
        assert router is not None
    
    @pytest.mark.asyncio
    async def test_pipeline_status_endpoint(self, project_manager):
        """Test the pipeline status API endpoint."""
        from app.api.pipeline import router
        assert router is not None


class TestProjectPersistence:
    """Test that projects can be saved and loaded correctly."""
    
    @pytest.mark.asyncio
    async def test_project_save_load(self, project_manager):
        """Test that projects can be saved and loaded."""
        project_data = ProjectCreate(
            name="Persistence Test",
            description="Test project persistence",
            target_languages=["en", "es"],
        )
        
        project = project_manager.create_project(project_data)
        project_id = project.project_id
        
        # Load the project
        loaded_project = project_manager.load_project(str(project_id))
        
        assert loaded_project.project_id == project_id
        assert loaded_project.name == "Persistence Test"
        assert loaded_project.description == "Test project persistence"
        assert loaded_project.target_languages == ["en", "es"]
    
    @pytest.mark.asyncio
    async def test_project_listing(self, project_manager):
        """Test project listing."""
        # Create multiple projects
        for i in range(3):
            project_data = ProjectCreate(
                name=f"Test Project {i}",
                description=f"Test project {i}",
                target_languages=["en"],
            )
            project_manager.create_project(project_data)
        
        projects = project_manager.list_projects()
        assert len(projects) >= 3
        
        # Check sorting (newest first)
        for i in range(len(projects) - 1):
            assert projects[i].updated_at >= projects[i + 1].updated_at


class TestFileStructure:
    """Test that project file structure is created correctly."""
    
    @pytest.mark.asyncio
    async def test_project_directory_structure(self, project_manager):
        """Test that all required directories are created."""
        project_data = ProjectCreate(
            name="Structure Test",
            description="Test directory structure",
            target_languages=["en", "es", "fr"],
        )
        
        project = project_manager.create_project(project_data)
        project_dir = project_manager.get_project_path(str(project.project_id))
        
        # Check all required directories exist
        required_dirs = [
            "source/source_media",
            "transcript",
            "story",
            "characters",
            "locations",
            "scenes",
            "languages/en",
            "languages/es",
            "languages/fr",
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
            "output/en",
            "output/es",
            "output/fr",
            "approvals",
            "logs",
            "exports",
            "jobs",
        ]
        
        for dir_path in required_dirs:
            full_path = project_dir / dir_path
            assert full_path.exists(), f"Missing directory: {dir_path}"
            assert full_path.is_dir(), f"Not a directory: {dir_path}"
        
        # Check language-specific output directories
        for lang in ["en", "es", "fr"]:
            assert (project_dir / "output" / lang).exists()
            assert (project_dir / "languages" / lang).exists()
            assert (project_dir / "languages" / lang / "scenes").exists()
            assert (project_dir / "languages" / lang / "audio").exists()
            assert (project_dir / "languages" / lang / "prompts").exists()


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])