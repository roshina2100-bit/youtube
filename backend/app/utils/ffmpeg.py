"""
FFmpeg wrapper for the Cinematic Video Studio.
Safe FFmpeg operations with argument validation.
"""

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.core.security import SafeSubprocess
from app.core.logging import get_project_logger


class FFmpegWrapper:
    """Safe FFmpeg wrapper for video/audio processing."""
    
    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe"):
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
    
    async def probe(self, input_path: str) -> Dict[str, Any]:
        """Probe media file for metadata."""
        cmd = [
            self.ffprobe_path,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            input_path
        ]
        
        SafeSubprocess.validate_command(cmd)
        
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"FFprobe failed: {result.stderr}")
            
            return json.loads(result.stdout)
            
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse FFprobe output: {e}")
        except subprocess.TimeoutExpired:
            raise RuntimeError("FFprobe timed out")
    
    async def get_duration(self, input_path: str) -> float:
        """Get media duration in seconds."""
        probe_data = await self.probe(input_path)
        format_info = probe_data.get("format", {})
        return float(format_info.get("duration", 0))
    
    async def get_video_info(self, input_path: str) -> Dict[str, Any]:
        """Get video stream info."""
        probe_data = await self.probe(input_path)
        
        for stream in probe_data.get("streams", []):
            if stream.get("codec_type") == "video":
                return {
                    "width": stream.get("width"),
                    "height": stream.get("height"),
                    "fps": self._parse_fps(stream.get("r_frame_rate", "0/1")),
                    "codec": stream.get("codec_name"),
                    "pix_fmt": stream.get("pix_fmt"),
                    "duration": float(stream.get("duration", 0)),
                }
        return {}
    
    async def get_audio_info(self, input_path: str) -> Dict[str, Any]:
        """Get audio stream info."""
        probe_data = await self.probe(input_path)
        
        for stream in probe_data.get("streams", []):
            if stream.get("codec_type") == "audio":
                return {
                    "codec": stream.get("codec_name"),
                    "sample_rate": int(stream.get("sample_rate", 0)),
                    "channels": stream.get("channels"),
                    "channel_layout": stream.get("channel_layout"),
                    "duration": float(stream.get("duration", 0)),
                }
        return {}
    
    def _parse_fps(self, fps_str: str) -> float:
        """Parse frame rate string (e.g., '30000/1001')."""
        try:
            if "/" in fps_str:
                num, den = fps_str.split("/")
                return float(num) / float(den)
            return float(fps_str)
        except Exception:
            return 0.0
    
    async def concat_videos(self, input_paths: List[str], output_path: str) -> None:
        """Concatenate multiple videos."""
        if not input_paths:
            raise ValueError("No input videos provided")
        
        if len(input_paths) == 1:
            # Single file, just copy
            await self.copy_video(input_paths[0], output_path)
            return
        
        # Create concat file list
        concat_file = Path(output_path).with_suffix(".txt")
        with open(concat_file, "w") as f:
            for path in input_paths:
                f.write(f"file '{Path(path).absolute()}'\n")
        
        try:
            cmd = [
                self.ffmpeg_path,
                "-y",  # Overwrite output
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-c", "copy",
                output_path
            ]
            
            SafeSubprocess.validate_command(cmd)
            
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"FFmpeg concat failed: {result.stderr}")
                
        finally:
            # Clean up concat file
            if concat_file.exists():
                concat_file.unlink()
    
    async def copy_video(self, input_path: str, output_path: str) -> None:
        """Copy video without re-encoding."""
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i", input_path,
            "-c", "copy",
            output_path
        ]
        
        SafeSubprocess.validate_command(cmd)
        
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg copy failed: {result.stderr}")
    
    async def trim_video(
        self, 
        input_path: str, 
        output_path: str, 
        start_time: float, 
        duration: Optional[float] = None,
        reencode: bool = False
    ) -> None:
        """Trim video to specified duration."""
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-ss", str(start_time),
            "-i", input_path,
        ]
        
        if duration:
            cmd.extend(["-t", str(duration)])
        
        if reencode:
            cmd.extend([
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "128k",
            ])
        else:
            cmd.extend(["-c", "copy"])
        
        cmd.append(output_path)
        
        SafeSubprocess.validate_command(cmd)
        
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg trim failed: {result.stderr}")
    
    async def scale_video(
        self,
        input_path: str,
        output_path: str,
        width: int,
        height: int,
        keep_aspect: bool = True
    ) -> None:
        """Scale video to specified dimensions."""
        if keep_aspect:
            vf = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
        else:
            vf = f"scale={width}:{height}"
        
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i", input_path,
            "-vf", vf,
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "copy",
            output_path
        ]
        
        SafeSubprocess.validate_command(cmd)
        
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg scale failed: {result.stderr}")
    
    async def change_fps(
        self,
        input_path: str,
        output_path: str,
        fps: int
    ) -> None:
        """Change video frame rate."""
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i", input_path,
            "-filter:v", f"fps={fps}",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "copy",
            output_path
        ]
        
        SafeSubprocess.validate_command(cmd)
        
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg fps change failed: {result.stderr}")
    
    async def mix_audio(
        self,
        audio_paths: List[str],
        output_path: str,
        volumes: Optional[List[float]] = None,
        normalize: bool = True
    ) -> None:
        """Mix multiple audio files."""
        if not audio_paths:
            raise ValueError("No audio files provided")
        
        if len(audio_paths) == 1:
            await self.copy_audio(audio_paths[0], output_path, normalize)
            return
        
        # Build filter complex for mixing
        filter_parts = []
        for i, path in enumerate(audio_paths):
            vol = volumes[i] if volumes and i < len(volumes) else 1.0
            filter_parts.append(f"[{i}:a]volume={vol}[a{i}]")
        
        # Mix all audio streams
        mix_inputs = "".join(f"[a{i}]" for i in range(len(audio_paths)))
        filter_parts.append(f"{mix_inputs}amix=inputs={len(audio_paths)}:duration=longest:normalize={1 if normalize else 0}[out]")
        
        filter_complex = ";".join(filter_parts)
        
        cmd = [
            self.ffmpeg_path,
            "-y",
        ]
        
        for path in audio_paths:
            cmd.extend(["-i", path])
        
        cmd.extend([
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-c:a", "pcm_s16le",  # Uncompressed WAV
            output_path
        ])
        
        SafeSubprocess.validate_command(cmd)
        
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg audio mix failed: {result.stderr}")
    
    async def copy_audio(
        self,
        input_path: str,
        output_path: str,
        normalize: bool = False
    ) -> None:
        """Copy audio, optionally normalize."""
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i", input_path,
        ]
        
        if normalize:
            cmd.extend(["-af", "loudnorm=I=-16:TP=-1.5:LRA=11"])
            cmd.extend(["-c:a", "pcm_s16le"])
        else:
            cmd.extend(["-c:a", "copy"])
        
        cmd.append(output_path)
        
        SafeSubprocess.validate_command(cmd)
        
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg audio copy failed: {result.stderr}")
    
    async def normalize_audio(
        self,
        input_path: str,
        output_path: str,
        target_lufs: float = -16.0
    ) -> None:
        """Normalize audio to target LUFS."""
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i", input_path,
            "-af", f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11:print_format=json",
            "-c:a", "pcm_s16le",
            output_path
        ]
        
        SafeSubprocess.validate_command(cmd)
        
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg normalize failed: {result.stderr}")
    
    async def mux_video_audio(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
        video_codec: str = "copy",
        audio_codec: str = "aac",
        audio_bitrate: str = "192k"
    ) -> None:
        """Mux video and audio into single file."""
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", video_codec,
            "-c:a", audio_codec,
            "-b:a", audio_bitrate,
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            output_path
        ]
        
        SafeSubprocess.validate_command(cmd)
        
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg mux failed: {result.stderr}")
    
    async def add_subtitles(
        self,
        video_path: str,
        subtitle_path: str,
        output_path: str,
        subtitle_style: Optional[str] = None
    ) -> None:
        """Burn subtitles into video."""
        vf = f"subtitles={subtitle_path}"
        if subtitle_style:
            vf += f":force_style='{subtitle_style}'"
        
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i", video_path,
            "-vf", vf,
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "copy",
            output_path
        ]
        
        SafeSubprocess.validate_command(cmd)
        
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg subtitles failed: {result.stderr}")
    
    async def extract_audio(
        self,
        video_path: str,
        output_path: str,
        codec: str = "pcm_s16le",
        sample_rate: int = 48000
    ) -> None:
        """Extract audio from video."""
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i", video_path,
            "-vn",
            "-acodec", codec,
            "-ar", str(sample_rate),
            output_path
        ]
        
        SafeSubprocess.validate_command(cmd)
        
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg extract audio failed: {result.stderr}")
    
    async def create_video_from_images(
        self,
        image_pattern: str,
        output_path: str,
        fps: int = 30,
        duration: Optional[float] = None
    ) -> None:
        """Create video from image sequence."""
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-framerate", str(fps),
            "-i", image_pattern,
        ]
        
        if duration:
            cmd.extend(["-t", str(duration)])
        
        cmd.extend([
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            output_path
        ])
        
        SafeSubprocess.validate_command(cmd)
        
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg image sequence failed: {result.stderr}")
    
    async def apply_transition(
        self,
        input1: str,
        input2: str,
        output_path: str,
        transition_type: str = "fade",
        duration: float = 1.0
    ) -> None:
        """Apply transition between two videos."""
        if transition_type == "fade":
            filter_complex = (
                f"[0:v]fade=t=out:st={duration}:d={duration}[v0];"
                f"[1:v]fade=t=in:st=0:d={duration}[v1];"
                f"[v0][v1]overlay[outv];"
                f"[0:a][1:a]acrossfade=d={duration}[outa]"
            )
        elif transition_type == "crossfade":
            filter_complex = (
                f"[0:v][1:v]xfade=transition=fade:duration={duration}:offset={duration}[outv];"
                f"[0:a][1:a]acrossfade=d={duration}[outa]"
            )
        else:
            raise ValueError(f"Unsupported transition: {transition_type}")
        
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i", input1,
            "-i", input2,
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-map", "[outa]",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "192k",
            output_path
        ]
        
        SafeSubprocess.validate_command(cmd)
        
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg transition failed: {result.stderr}")
    
    async def export_video(
        self,
        input_path: str,
        output_path: str,
        preset: str = "medium",
        crf: int = 23,
        codec: str = "libx264",
        audio_codec: str = "aac",
        audio_bitrate: str = "192k"
    ) -> None:
        """Export video with specified encoding settings."""
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i", input_path,
            "-c:v", codec,
            "-preset", preset,
            "-crf", str(crf),
            "-c:a", audio_codec,
            "-b:a", audio_bitrate,
            "-movflags", "+faststart",
            output_path
        ]
        
        SafeSubprocess.validate_command(cmd)
        
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg export failed: {result.stderr}")