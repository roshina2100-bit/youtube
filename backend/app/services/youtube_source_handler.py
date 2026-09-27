"""
YouTube Source Handler for the Cinematic Video Studio.
Handles YouTube URL import, metadata extraction, and transcript downloading.
"""

import asyncio
import re
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime

from app.services.project_manager import ProjectManager
from app.workflow.engine import WorkflowEngine
from app.models.job import Job, JobType
from app.core.config import get_settings
from app.core.security import sanitize_filename
from app.utils.ffmpeg import FFmpegWrapper


class YouTubeSourceHandler:
    """Handler for YouTube URL source import."""
    
    # YouTube URL patterns
    YOUTUBE_PATTERNS = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/v/([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
    ]
    
    def __init__(
        self, 
        project_manager: ProjectManager, 
        workflow_engine: WorkflowEngine
    ):
        self.project_manager = project_manager
        self.workflow_engine = workflow_engine
        self._settings = get_settings()
        self.ffmpeg = FFmpegWrapper(self._settings.ffmpeg_path)
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """Extract YouTube video ID from URL."""
        for pattern in self.YOUTUBE_PATTERNS:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def is_youtube_url(self, url: str) -> bool:
        """Check if URL is a YouTube URL."""
        return self.extract_video_id(url) is not None
    
    async def get_video_info(self, video_id: str) -> Dict[str, Any]:
        """Get video metadata using yt-dlp."""
        try:
            import yt_dlp
            
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f'https://www.youtube.com/watch?v={video_id}', download=False)
                
                return {
                    'id': info.get('id'),
                    'title': info.get('title'),
                    'description': info.get('description'),
                    'duration': info.get('duration'),
                    'uploader': info.get('uploader'),
                    'uploader_id': info.get('uploader_id'),
                    'upload_date': info.get('upload_date'),
                    'view_count': info.get('view_count'),
                    'like_count': info.get('like_count'),
                    'channel': info.get('channel'),
                    'channel_id': info.get('channel_id'),
                    'tags': info.get('tags', []),
                    'categories': info.get('categories', []),
                    'thumbnail': info.get('thumbnail'),
                    'thumbnails': info.get('thumbnails', []),
                    'formats': info.get('formats', []),
                }
        except ImportError:
            raise RuntimeError("yt-dlp not installed. Install with: pip install yt-dlp")
        except Exception as e:
            raise RuntimeError(f"Failed to get video info: {str(e)}")
    
    async def download_video(
        self, 
        video_id: str, 
        output_path: Path,
        quality: str = 'best[height<=1080]',
    ) -> Dict[str, Any]:
        """Download video from YouTube."""
        try:
            import yt_dlp
            
            output_template = str(output_path / '%(title)s.%(ext)s')
            
            ydl_opts = {
                'format': quality,
                'outtmpl': output_template,
                'quiet': True,
                'no_warnings': True,
                'writeinfojson': True,
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': ['en', 'en-US', 'en-GB'],
                'subtitlesformat': 'vtt',
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f'https://www.youtube.com/watch?v={video_id}', download=True)
                
                # Find downloaded file
                downloaded_files = list(Path(ydl_opts['outtmpl']).parent.glob('*'))
                video_file = None
                for f in downloaded_files:
                    if f.suffix in ['.mp4', '.mkv', '.webm', '.mov']:
                        video_file = f
                        break
                
                if not video_file:
                    raise RuntimeError("Video file not found after download")
                
                return {
                    'file_path': str(video_file),
                    'title': info.get('title'),
                    'duration': info.get('duration'),
                    'metadata': info,
                }
        except ImportError:
            raise RuntimeError("yt-dlp not installed. Install with: pip install yt-dlp")
        except Exception as e:
            raise RuntimeError(f"Failed to download video: {str(e)}")
    
    async def download_transcript(
        self, 
        video_id: str, 
        output_path: Path,
        languages: List[str] = ['en', 'en-US', 'en-GB'],
    ) -> Optional[Path]:
        """Download transcript/subtitles from YouTube."""
        try:
            import yt_dlp
            
            ydl_opts = {
                'skip_download': True,
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': languages,
                'subtitlesformat': 'vtt',
                'outtmpl': str(output_path / '%(title)s.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([f'https://www.youtube.com/watch?v={video_id}'])
            
            # Find subtitle file
            subtitle_files = list(output_path.glob('*.vtt'))
            if subtitle_files:
                return subtitle_files[0]
            
            return None
        except ImportError:
            raise RuntimeError("yt-dlp not installed. Install with: pip install yt-dlp")
        except Exception as e:
            raise RuntimeError(f"Failed to download transcript: {str(e)}")
    
    async def import_youtube_url(
        self,
        project_id: UUID,
        url: str,
        download_video: bool = True,
        download_transcript: bool = True,
        quality: str = 'best[height<=1080]',
    ) -> Dict[str, Any]:
        """Import a YouTube URL as project source."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        
        # Extract video ID
        video_id = self.extract_video_id(url)
        if not video_id:
            raise ValueError(f"Invalid YouTube URL: {url}")
        
        # Get video info
        video_info = await self.get_video_info(video_id)
        
        source_dir = project_dir / "source" / "source_media"
        source_dir.mkdir(parents=True, exist_ok=True)
        
        result = {
            'source_type': 'youtube',
            'url': url,
            'video_id': video_id,
            'title': video_info.get('title'),
            'duration_seconds': video_info.get('duration', 0),
            'metadata': video_info,
        }
        
        # Download video if requested
        if download_video:
            try:
                download_result = await self.download_video(video_id, source_dir)
                result['video_path'] = f"source/source_media/{Path(download_result['file_path']).name}"
                result['video_file'] = download_result['file_path']
            except Exception as e:
                result['video_error'] = str(e)
        
        # Download transcript if requested
        if download_transcript:
            try:
                transcript_dir = project_dir / "transcript"
                transcript_dir.mkdir(parents=True, exist_ok=True)
                
                transcript_path = await self.download_transcript(video_id, transcript_dir)
                if transcript_path:
                    result['transcript_path'] = f"transcript/{transcript_path.name}"
                    result['transcript_file'] = str(transcript_path)
            except Exception as e:
                result['transcript_error'] = str(e)
        
        # Update project manifest
        project = self.project_manager.load_project(str(project_id))
        project.source = {
            "type": "youtube",
            "url": url,
            "video_id": video_id,
            "original_filename": f"{video_info.get('title', 'youtube_video')}.mp4",
            "duration_seconds": video_info.get('duration', 0),
            "metadata": video_info,
            "youtube_result": result,
        }
        self.project_manager.save_project(
            self.project_manager.get_project_path(str(project_id)), 
            project
        )
        
        # Create source import job
        job = Job(
            project_id=project_id,
            type=JobType.SOURCE_IMPORT,
            input={"url": url, "video_id": video_id, "source_type": "youtube"},
        )
        await self.workflow_engine.submit_job(job)
        
        return result
    
    async def process_youtube_pipeline(
        self,
        project_id: UUID,
        url: str,
        target_languages: List[str] = None,
        providers: Dict[str, str] = None,
    ) -> Dict[str, Any]:
        """Complete YouTube pipeline: import -> transcript -> story -> characters -> scenes -> translate -> render."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        
        # Step 1: Import YouTube URL
        import_result = await self.import_youtube_url(
            project_id, url, 
            download_video=True, 
            download_transcript=True
        )
        
        if 'video_error' in import_result:
            return {"success": False, "error": f"Video download failed: {import_result['video_error']}"}
        
        # Step 2: Process transcript
        transcript_result = await self._process_transcript_pipeline(project_id)
        
        # Step 3: Detect language
        lang_result = await self._detect_language_pipeline(project_id)
        
        # Step 4: Analyze story
        story_result = await self._analyze_story_pipeline(project_id)
        
        # Step 5: Extract characters
        char_result = await self._extract_characters_pipeline(project_id)
        
        # Step 6: Generate scenes
        scene_result = await self._generate_scenes_pipeline(project_id)
        
        # Step 7: Generate prompts
        prompt_result = await self._generate_prompts_pipeline(project_id)
        
        # Step 8: Generate images
        image_result = await self._generate_images_pipeline(project_id)
        
        # Step 9: Generate videos
        video_result = await self._generate_videos_pipeline(project_id)
        
        # Step 10: Generate silent master
        master_result = await self._generate_silent_master_pipeline(project_id)
        
        # Step 11: Translate (if target languages specified)
        if target_languages:
            translate_result = await self._translate_pipeline(project_id, target_languages)
        else:
            translate_result = {"skipped": True}
        
        # Step 12: Generate audio
        audio_result = await self._generate_audio_pipeline(project_id)
        
        # Step 13: Render final videos
        render_result = await self._render_final_pipeline(project_id)
        
        return {
            "success": True,
            "import": import_result,
            "transcript": transcript_result,
            "language_detection": lang_result,
            "story": story_result,
            "characters": char_result,
            "scenes": scene_result,
            "prompts": prompt_result,
            "images": image_result,
            "videos": video_result,
            "silent_master": master_result,
            "translation": translate_result,
            "audio": audio_result,
            "render": render_result,
        }
    
    # Pipeline step methods
    async def _process_transcript_pipeline(self, project_id: UUID) -> Dict[str, Any]:
        """Process transcript through normalization and language detection."""
        job = Job(
            project_id=project_id,
            type=JobType.TRANSCRIPT_PROCESS,
            input={},
        )
        await self.workflow_engine.submit_job(job)
        return {"job_id": job.job_id, "status": "started"}
    
    async def _detect_language_pipeline(self, project_id: UUID) -> Dict[str, Any]:
        """Detect language of transcript."""
        job = Job(
            project_id=project_id,
            type=JobType.LANGUAGE_DETECT,
            input={},
        )
        await self.workflow_engine.submit_job(job)
        return {"job_id": job.job_id, "status": "started"}
    
    async def _analyze_story_pipeline(self, project_id: UUID) -> Dict[str, Any]:
        """Analyze story from transcript."""
        job = Job(
            project_id=project_id,
            type=JobType.STORY_ANALYSIS,
            input={},
        )
        await self.workflow_engine.submit_job(job)
        return {"job_id": job.job_id, "status": "started"}
    
    async def _extract_characters_pipeline(self, project_id: UUID) -> Dict[str, Any]:
        """Extract characters from story."""
        job = Job(
            project_id=project_id,
            type=JobType.CHARACTER_EXTRACTION,
            input={},
        )
        await self.workflow_engine.submit_job(job)
        return {"job_id": job.job_id, "status": "started"}
    
    async def _generate_scenes_pipeline(self, project_id: UUID) -> Dict[str, Any]:
        """Generate cinematic scenes."""
        job = Job(
            project_id=project_id,
            type=JobType.SCENE_GENERATION,
            input={},
        )
        await self.workflow_engine.submit_job(job)
        return {"job_id": job.job_id, "status": "started"}
    
    async def _generate_prompts_pipeline(self, project_id: UUID) -> Dict[str, Any]:
        """Generate cinematic prompts for all scenes."""
        job = Job(
            project_id=project_id,
            type=JobType.SCENE_PROMPT_GEN,
            input={},
        )
        await self.workflow_engine.submit_job(job)
        return {"job_id": job.job_id, "status": "started"}
    
    async def _generate_images_pipeline(self, project_id: UUID) -> Dict[str, Any]:
        """Generate images for all scenes."""
        job = Job(
            project_id=project_id,
            type=JobType.IMAGE_GENERATION,
            input={},
        )
        await self.workflow_engine.submit_job(job)
        return {"job_id": job.job_id, "status": "started"}
    
    async def _generate_videos_pipeline(self, project_id: UUID) -> Dict[str, Any]:
        """Generate videos for all scenes."""
        job = Job(
            project_id=project_id,
            type=JobType.VIDEO_GENERATION,
            input={},
        )
        await self.workflow_engine.submit_job(job)
        return {"job_id": job.job_id, "status": "started"}
    
    async def _generate_silent_master_pipeline(self, project_id: UUID) -> Dict[str, Any]:
        """Generate silent master video."""
        job = Job(
            project_id=project_id,
            type=JobType.SILENT_MASTER,
            input={},
        )
        await self.workflow_engine.submit_job(job)
        return {"job_id": job.job_id, "status": "started"}
    
    async def _translate_pipeline(self, project_id: UUID, target_languages: List[str]) -> Dict[str, Any]:
        """Translate all scenes to target languages."""
        job = Job(
            project_id=project_id,
            type=JobType.TRANSLATION,
            input={"target_languages": target_languages},
        )
        await self.workflow_engine.submit_job(job)
        return {"job_id": job.job_id, "status": "started"}
    
    async def _generate_audio_pipeline(self, project_id: UUID) -> Dict[str, Any]:
        """Generate audio for all languages."""
        job = Job(
            project_id=project_id,
            type=JobType.TTS_GENERATION,
            input={},
        )
        await self.workflow_engine.submit_job(job)
        return {"job_id": job.job_id, "status": "started"}
    
    async def _render_final_pipeline(self, project_id: UUID) -> Dict[str, Any]:
        """Render final videos for all languages."""
        job = Job(
            project_id=project_id,
            type=JobType.FINAL_RENDER,
            input={},
        )
        await self.workflow_engine.submit_job(job)
        return {"job_id": job.job_id, "status": "started"}