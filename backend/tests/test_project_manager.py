"""Unit tests for ProjectManager."""

import pytest
from pathlib import Path
from uuid import UUID

from app.services.project_manager import ProjectManager
from app.models.project import ProjectCreate, ProjectStatus


class TestProjectManager:
    """Tests for ProjectManager."""

    def test_create_project(self, project_manager, sample_project_data):
        """Test creating a new project."""
        project_data = ProjectCreate(**sample_project_data)
        project = project_manager.create_project(project_data)

        assert project.name == sample_project_data["name"]
        assert project.description == sample_project_data["description"]
        assert project.target_languages == sample_project_data["target_languages"]
        assert project.status == ProjectStatus.DRAFT
        assert isinstance(project.project_id, UUID)

        # Check project directory was created
        project_dir = project_manager.get_project_path(str(project.project_id))
        assert project_dir.exists()
        assert (project_dir / "project.json").exists()

    def test_create_project_duplicate_name(self, project_manager, sample_project_data):
        """Test creating project with duplicate name adds suffix."""
        project_data = ProjectCreate(**sample_project_data)
        project1 = project_manager.create_project(project_data)
        project2 = project_manager.create_project(project_data)

        assert project1.project_id != project2.project_id
        assert project2.name != project1.name

    def test_load_project(self, project_manager, sample_project_data):
        """Test loading an existing project."""
        project_data = ProjectCreate(**sample_project_data)
        created = project_manager.create_project(project_data)

        loaded = project_manager.load_project(str(created.project_id))

        assert loaded.project_id == created.project_id
        assert loaded.name == created.name
        assert loaded.description == created.description

    def test_load_nonexistent_project(self, project_manager):
        """Test loading a non-existent project raises error."""
        with pytest.raises(FileNotFoundError):
            project_manager.load_project("00000000-0000-0000-0000-000000000000")

    def test_list_projects(self, project_manager, sample_project_data):
        """Test listing projects."""
        project_data = ProjectCreate(**sample_project_data)
        project_manager.create_project(project_data)

        projects = project_manager.list_projects()

        assert len(projects) >= 1
        assert any(p.name == sample_project_data["name"] for p in projects)

    def test_delete_project(self, project_manager, sample_project_data):
        """Test deleting a project."""
        project_data = ProjectCreate(**sample_project_data)
        project = project_manager.create_project(project_data)

        result = project_manager.delete_project(str(project.project_id))

        assert result is True
        assert not project_manager.get_project_path(str(project.project_id)).exists()

        with pytest.raises(FileNotFoundError):
            project_manager.load_project(str(project.project_id))

    def test_project_folder_structure(self, project_manager, sample_project_data):
        """Test that all required folders are created."""
        project_data = ProjectCreate(**sample_project_data)
        project = project_manager.create_project(project_data)

        project_dir = project_manager.get_project_path(str(project.project_id))

        required_folders = [
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

        for folder in required_folders:
            folder_path = project_dir / folder
            assert folder_path.exists(), f"Missing folder: {folder}"
            assert folder_path.is_dir(), f"Not a directory: {folder}"

    def test_language_directories_created(self, project_manager):
        """Test that language-specific directories are created."""
        project_data = ProjectCreate(
            name="Test",
            target_languages=["en", "es", "fr"],
        )
        project = project_manager.create_project(project_data)

        project_dir = project_manager.get_project_path(str(project.project_id))

        for lang in ["en", "es", "fr"]:
            assert (project_dir / "languages" / lang).exists()
            assert (project_dir / "languages" / lang / "scenes").exists()
            assert (project_dir / "languages" / lang / "audio").exists()
            assert (project_dir / "languages" / lang / "prompts").exists()
            assert (project_dir / "output" / lang).exists()

    def test_save_and_load_transcript(self, project_manager, sample_project_data):
        """Test saving and loading transcript data."""
        from app.models.transcript import TranscriptData, TranscriptSegment

        project_data = ProjectCreate(**sample_project_data)
        project = project_manager.create_project(project_data)
        project_dir = project_manager.get_project_path(str(project.project_id))

        transcript = TranscriptData(
            segments=[
                TranscriptSegment(id="seg_001", start=0.0, end=5.0, text="Hello world"),
                TranscriptSegment(id="seg_002", start=5.0, end=10.0, text="How are you?"),
            ],
            total_duration=10.0,
            language="en",
        )

        project_manager.save_transcript(project_dir, transcript)
        loaded = project_manager.load_transcript(project_dir)

        assert loaded is not None
        assert len(loaded.segments) == 2
        assert loaded.segments[0].text == "Hello world"
        assert loaded.language == "en"

    def test_validate_project_structure(self, project_manager, sample_project_data):
        """Test project structure validation."""
        project_data = ProjectCreate(**sample_project_data)
        project = project_manager.create_project(project_data)
        project_dir = project_manager.get_project_path(str(project.project_id))

        valid, errors = project_manager.validate_project_structure(project_dir)

        assert valid is True
        assert len(errors) == 0

    def test_repair_project_structure(self, project_manager, sample_project_data):
        """Test repairing missing folders."""
        project_data = ProjectCreate(**sample_project_data)
        project = project_manager.create_project(project_data)
        project_dir = project_manager.get_project_path(str(project.project_id))

        # Remove a folder
        (project_dir / "transcript").rmdir()

        valid, errors = project_manager.validate_project_structure(project_dir)
        assert valid is False

        created = project_manager.repair_project_structure(project_dir)
        assert "transcript" in created

        valid, errors = project_manager.validate_project_structure(project_dir)
        assert valid is True

    def test_compute_file_hash(self, project_manager, sample_project_data, tmp_path):
        """Test file hash computation."""
        project_data = ProjectCreate(**sample_project_data)
        project = project_manager.create_project(project_data)
        project_dir = project_manager.get_project_path(str(project.project_id))

        # Create a test file
        test_file = project_dir / "test.txt"
        test_file.write_text("Hello, World!")

        hash_value = project_manager.compute_file_hash(test_file)

        assert len(hash_value) == 64  # SHA-256 hex length
        assert hash_value == "dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f"

    def test_get_next_version(self, project_manager, sample_project_data):
        """Test version numbering."""
        project_data = ProjectCreate(**sample_project_data)
        project = project_manager.create_project(project_data)
        project_dir = project_manager.get_project_path(str(project.project_id))

        # Create some versioned files
        (project_dir / "prompts" / "characters").mkdir(parents=True, exist_ok=True)
        (project_dir / "prompts" / "characters" / "char_001_prompt_v001.txt").write_text("v1")
        (project_dir / "prompts" / "characters" / "char_001_prompt_v002.txt").write_text("v2")

        next_version = project_manager.get_next_version(project_dir, "char_001_prompt", "prompts/characters")

        assert next_version == "v003"