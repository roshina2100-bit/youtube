"""Pytest configuration for Cinematic Video Studio backend tests."""

import pytest
import asyncio
from pathlib import Path
import tempfile
import shutil

from app.services.project_manager import ProjectManager
from app.providers.registry import ProviderRegistry
from app.workflow.engine import WorkflowEngine
from app.services.youtube_source_handler import YouTubeSourceHandler
from app.services.pipeline_completion_service import PipelineCompletionService
from app.models.job import Job, JobType, JobStatus
from app.core.config import Settings
from app.models.project import ProjectCreate


# Test configuration
TEST_PROJECT_NAME = "Test YouTube Pipeline"
TEST_YOUTUBE_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Roll - famous test video
TEST_TARGET_LANGUAGES = ["en", "es", "fr"]


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


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


@pytest.fixture
def sample_project_data():
    """Sample project creation data."""
    return {
        "name": "Test Project",
        "description": "A test project for unit tests",
        "target_languages": ["en", "es", "fr"],
    }


# Test markers
def pytest_configure(config):
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "gpu: Tests requiring GPU")