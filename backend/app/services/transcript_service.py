"""
Transcript Service for the Cinematic Video Studio.
Handles transcript processing, normalization, language detection, and segmentation.
"""

import asyncio
import json
import re
from pathlib import Path
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime

from app.services.project_manager import ProjectManager
from app.workflow.engine import WorkflowEngine
from app.models.job import Job, JobType
from app.models.transcript import TranscriptData, TranscriptSegment, LanguageDetectionResult, SpeakerInfo
from app.providers.registry import ProviderRegistry
from app.models.provider import ProviderType
from app.core.config import get_settings


class TranscriptService:
    """Service for transcript processing and management."""
    
    def __init__(
        self, 
        project_manager: ProjectManager, 
        workflow_engine: WorkflowEngine,
        provider_registry: ProviderRegistry
    ):
        self.project_manager = project_manager
        self.workflow_engine = workflow_engine
        self.provider_registry = provider_registry
        self._settings = get_settings()
    
    async def process_transcript(
        self,
        project_id: UUID,
        format: str = "txt",
        language: Optional[str] = None,
    ) -> TranscriptData:
        """Process and normalize transcript."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        transcript_dir = project_dir / "transcript"
        
        # Load original transcript
        original_path = transcript_dir / "original.txt"
        if not original_path.exists():
            raise FileNotFoundError("No original transcript found")
        
        content = original_path.read_text(encoding='utf-8')
        
        # Parse based on format
        if format == "srt":
            segments = self._parse_srt(content)
        elif format == "vtt":
            segments = self._parse_vtt(content)
        elif format == "json":
            segments = self._parse_json(content)
        else:
            # Plain text - create single segment
            segments = [TranscriptSegment(
                id="seg_001",
                start=0.0,
                end=0.0,
                text=content.strip(),
                speaker=None,
                language=language,
                confidence=1.0
            )]
        
        # Detect language if not provided
        if not language:
            detection = await self.detect_language(project_id, content)
            language = detection.detected_language
        
        # Normalize segments
        normalized_segments = await self._normalize_segments(segments, language)
        
        # Create transcript data
        transcript = TranscriptData(
            segments=normalized_segments,
            speakers=self._extract_speakers(normalized_segments),
            total_duration=sum(s.duration for s in normalized_segments),
            language=language,
            normalized=True,
            source_format=format,
        )
        
        # Save transcript
        self.project_manager.save_transcript(
            self.project_manager.get_project_path(str(project_id)), 
            transcript
        )
        
        # Save language detection
        if not language:
            detection = await self.detect_language(project_id, content)
            self.project_manager.save_language_detection(
                self.project_manager.get_project_path(str(project_id)),
                detection
            )
        
        return transcript
    
    def _parse_srt(self, content: str) -> List[TranscriptSegment]:
        """Parse SRT format transcript."""
        segments = []
        blocks = content.strip().split('\n\n')
        
        for i, block in enumerate(blocks):
            lines = block.strip().split('\n')
            if len(lines) < 3:
                continue
            
            # Parse timestamp line
            timestamp_line = lines[1]
            match = re.match(r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})', timestamp_line)
            if not match:
                continue
            
            start = self._parse_srt_time(match.group(1))
            end = self._parse_srt_time(match.group(2))
            text = '\n'.join(lines[2:]).strip()
            
            segments.append(TranscriptSegment(
                id=f"seg_{i+1:03d}",
                start=start,
                end=end,
                text=text,
                speaker=None,
                language=None,
                confidence=1.0
            ))
        
        return segments
    
    def _parse_vtt(self, content: str) -> List[TranscriptSegment]:
        """Parse VTT format transcript."""
        segments = []
        lines = content.strip().split('\n')
        
        i = 0
        seg_num = 0
        while i < len(lines):
            line = lines[i].strip()
            if '-->' in line:
                match = re.match(r'(\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}\.\d{3})', line)
                if match:
                    start = self._parse_vtt_time(match.group(1))
                    end = self._parse_vtt_time(match.group(2))
                    
                    # Collect text lines
                    text_lines = []
                    i += 1
                    while i < len(lines) and lines[i].strip():
                        text_lines.append(lines[i].strip())
                        i += 1
                    
                    text = '\n'.join(text_lines).strip()
                    if text:
                        seg_num += 1
                        segments.append(TranscriptSegment(
                            id=f"seg_{seg_num:03d}",
                            start=start,
                            end=end,
                            text=text,
                            speaker=None,
                            language=None,
                            confidence=1.0
                        ))
            i += 1
        
        return segments
    
    def _parse_json(self, content: str) -> List[TranscriptSegment]:
        """Parse JSON format transcript."""
        data = json.loads(content)
        segments = []
        
        if isinstance(data, list):
            for i, item in enumerate(data):
                segments.append(TranscriptSegment(
                    id=item.get("id", f"seg_{i+1:03d}"),
                    start=item.get("start", 0.0),
                    end=item.get("end", 0.0),
                    text=item.get("text", ""),
                    speaker=item.get("speaker"),
                    language=item.get("language"),
                    confidence=item.get("confidence", 1.0)
                ))
        elif isinstance(data, dict) and "segments" in data:
            for i, item in enumerate(data["segments"]):
                segments.append(TranscriptSegment(
                    id=item.get("id", f"seg_{i+1:03d}"),
                    start=item.get("start", 0.0),
                    end=item.get("end", 0.0),
                    text=item.get("text", ""),
                    speaker=item.get("speaker"),
                    language=item.get("language"),
                    confidence=item.get("confidence", 1.0)
                ))
        
        return segments
    
    def _parse_srt_time(self, time_str: str) -> float:
        """Parse SRT time format (HH:MM:SS,mmm)."""
        time_part, ms_part = time_str.split(',')
        h, m, s = map(int, time_part.split(':'))
        return h * 3600 + m * 60 + s + int(ms_part) / 1000
    
    def _parse_vtt_time(self, time_str: str) -> float:
        """Parse VTT time format (HH:MM:SS.mmm)."""
        if '.' in time_str:
            time_part, ms_part = time_str.split('.')
        else:
            time_part, ms_part = time_str, '0'
        h, m, s = map(int, time_part.split(':'))
        return h * 3600 + m * 60 + s + int(ms_part) / 1000
    
    async def _normalize_segments(
        self, 
        segments: List[TranscriptSegment], 
        language: str
    ) -> List[TranscriptSegment]:
        """Normalize transcript segments."""
        normalized = []
        
        for seg in segments:
            # Clean text
            text = self._clean_text(seg.text)
            if not text:
                continue
            
            # Fix punctuation
            text = self._fix_punctuation(text)
            
            normalized.append(TranscriptSegment(
                id=seg.id,
                start=seg.start,
                end=seg.end,
                text=text,
                speaker=seg.speaker,
                language=language,
                confidence=seg.confidence
            ))
        
        return normalized
    
    def _clean_text(self, text: str) -> str:
        """Clean transcript text."""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep punctuation
        text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\'\"\(\)]', '', text)
        return text.strip()
    
    def _fix_punctuation(self, text: str) -> str:
        """Fix common punctuation issues."""
        # Ensure sentence ends with punctuation
        if text and text[-1] not in '.!?':
            text += '.'
        # Fix multiple spaces
        text = re.sub(r'\s+', ' ', text)
        return text
    
    def _extract_speakers(self, segments: List[TranscriptSegment]) -> List[SpeakerInfo]:
        """Extract speaker information from segments."""
        speakers = {}
        for seg in segments:
            if seg.speaker:
                if seg.speaker not in speakers:
                    speakers[seg.speaker] = SpeakerInfo(
                        id=seg.speaker,
                        name=seg.speaker,
                        segments_count=0,
                        total_duration=0.0
                    )
                speakers[seg.speaker].segments_count += 1
                speakers[seg.speaker].total_duration += seg.duration
        
        return list(speakers.values())
    
    async def detect_language(
        self, 
        project_id: UUID, 
        text: Optional[str] = None
    ) -> LanguageDetectionResult:
        """Detect language of transcript."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        
        if text is None:
            transcript = self.project_manager.load_transcript(project_dir)
            if not transcript:
                raise ValueError("No transcript found")
            text = transcript.get_text()
        
        # Get language detection provider
        provider = self.provider_registry.get_provider(
            ProviderType.LANGUAGE_DETECTION, "local_python", "lid.176"
        )
        
        if not provider:
            await self.provider_registry.load_provider(
                ProviderType.LANGUAGE_DETECTION, "local_python", "lid.176"
            )
            provider = self.provider_registry.get_provider(
                ProviderType.LANGUAGE_DETECTION, "local_python", "lid.176"
            )
        
        if not provider or not provider.is_available():
            # Fallback: simple heuristic
            return self._heuristic_language_detection(text)
        
        result = await provider.detect_text(text)
        
        if result.success:
            data = result.data
            return LanguageDetectionResult(
                detected_language=data.get("language", "en"),
                confidence=data.get("confidence", 0.0),
                detector=f"local_python:{provider.metadata.model_name}",
                alternatives=data.get("alternatives", []),
                manual_override=False
            )
        else:
            return self._heuristic_language_detection(text)
    
    def _heuristic_language_detection(self, text: str) -> LanguageDetectionResult:
        """Simple heuristic language detection."""
        # Check for common scripts
        if any('\u0900' <= c <= '\u097F' for c in text):  # Devanagari
            return LanguageDetectionResult(
                detected_language="hi",
                confidence=0.9,
                detector="heuristic",
                alternatives=[],
                manual_override=False
            )
        elif any('\u0C00' <= c <= '\u0C7F' for c in text):  # Telugu
            return LanguageDetectionResult(
                detected_language="te",
                confidence=0.9,
                detector="heuristic",
                alternatives=[],
                manual_override=False
            )
        elif any('\u0B80' <= c <= '\u0BFF' for c in text):  # Tamil
            return LanguageDetectionResult(
                detected_language="ta",
                confidence=0.9,
                detector="heuristic",
                alternatives=[],
                manual_override=False
            )
        else:
            return LanguageDetectionResult(
                detected_language="en",
                confidence=0.8,
                detector="heuristic",
                alternatives=[],
                manual_override=False
            )
    
    async def normalize_transcript(
        self,
        project_id: UUID,
        remove_filler_words: bool = True,
        fix_punctuation: bool = True,
        standardize_speakers: bool = True,
        merge_short_segments: bool = True,
        min_segment_duration: float = 0.5,
    ) -> TranscriptData:
        """Normalize existing transcript."""
        project_dir = self.project_manager.get_project_path(str(project_id))
        transcript = self.project_manager.load_transcript(project_dir)
        
        if not transcript:
            raise ValueError("No transcript found")
        
        segments = transcript.segments
        
        if remove_filler_words:
            segments = self._remove_filler_words(segments)
        
        if fix_punctuation:
            segments = [self._fix_segment_punctuation(s) for s in segments]
        
        if standardize_speakers:
            segments = self._standardize_speakers(segments)
        
        if merge_short_segments:
            segments = self._merge_short_segments(segments, min_segment_duration)
        
        # Update transcript
        transcript.segments = segments
        transcript.speakers = self._extract_speakers(segments)
        transcript.total_duration = sum(s.duration for s in segments)
        transcript.normalized = True
        transcript.updated_at = datetime.utcnow()
        
        self.project_manager.save_transcript(
            self.project_manager.get_project_path(str(project_id)), 
            transcript
        )
        
        return transcript
    
    def _remove_filler_words(self, segments: List[TranscriptSegment]) -> List[TranscriptSegment]:
        """Remove common filler words."""
        filler_words = {'um', 'uh', 'er', 'ah', 'like', 'you know', 'so', 'well', 'actually', 'basically', 'literally'}
        
        cleaned = []
        for seg in segments:
            words = seg.text.split()
            filtered = [w for w in words if w.lower().strip('.,!?') not in filler_words]
            if filtered:
                cleaned.append(TranscriptSegment(
                    id=seg.id,
                    start=seg.start,
                    end=seg.end,
                    text=' '.join(filtered),
                    speaker=seg.speaker,
                    language=seg.language,
                    confidence=seg.confidence
                ))
        return cleaned
    
    def _fix_segment_punctuation(self, segment: TranscriptSegment) -> TranscriptSegment:
        """Fix punctuation in a segment."""
        text = segment.text
        text = self._clean_text(text)
        text = self._fix_punctuation(text)
        return TranscriptSegment(
            id=segment.id,
            start=segment.start,
            end=segment.end,
            text=text,
            speaker=segment.speaker,
            language=segment.language,
            confidence=segment.confidence
        )
    
    def _standardize_speakers(self, segments: List[TranscriptSegment]) -> List[TranscriptSegment]:
        """Standardize speaker labels."""
        speaker_map = {}
        counter = 1
        
        for seg in segments:
            if seg.speaker:
                if seg.speaker not in speaker_map:
                    speaker_map[seg.speaker] = f"Speaker {counter}"
                    counter += 1
                seg.speaker = speaker_map[seg.speaker]
        return segments
    
    def _merge_short_segments(
        self, 
        segments: List[TranscriptSegment], 
        min_duration: float
    ) -> List[TranscriptSegment]:
        """Merge segments shorter than min_duration."""
        if not segments:
            return segments
        
        merged = []
        current = segments[0]
        
        for next_seg in segments[1:]:
            if current.duration < min_duration and current.speaker == next_seg.speaker:
                # Merge with next
                current = TranscriptSegment(
                    id=current.id,
                    start=current.start,
                    end=next_seg.end,
                    text=current.text + ' ' + next_seg.text,
                    speaker=current.speaker,
                    language=current.language,
                    confidence=min(current.confidence, next_seg.confidence)
                )
            else:
                merged.append(current)
                current = next_seg
        
        merged.append(current)
        return merged