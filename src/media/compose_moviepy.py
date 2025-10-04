"""
Video composition module using MoviePy for creating final videos.
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from moviepy.editor import (
    VideoFileClip, AudioFileClip, CompositeVideoClip,
    TextClip, concatenate_videoclips, ImageClip
)
from moviepy.video.fx import resize, crop
from moviepy.audio.fx import volumex

from utils.logger import get_logger
from utils.io import get_output_path
from utils.retry import retry


class VideoComposer:
    """Handles video composition and editing using MoviePy."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_logger("video_composer")
        
        # Video settings
        video_config = config.get("video", {})
        self.width = video_config.get("resolution", {}).get("width", 1080)
        self.height = video_config.get("resolution", {}).get("height", 1920)
        self.fps = video_config.get("fps", 30)
        self.bitrate = video_config.get("bitrate", "5000k")
        self.format = video_config.get("format", "mp4")
        
        # Audio settings
        audio_config = config.get("audio", {})
        self.audio_sample_rate = audio_config.get("sample_rate", 44100)
        self.audio_bitrate = audio_config.get("bitrate", "128k")
    
    async def compose_video(
        self,
        audio_path: str,
        broll_paths: List[str],
        subtitle_timings: List[Dict[str, Any]],
        output_filename: Optional[str] = None
    ) -> str:
        """Compose final video with audio, B-roll, and subtitles."""
        
        if not output_filename:
            timestamp = asyncio.get_event_loop().time()
            output_filename = f"video_{int(timestamp)}.{self.format}"
        
        output_path = get_output_path(self.config, output_filename)
        
        try:
            self.logger.info("Starting video composition...")
            
            # Load audio
            audio_clip = await self._load_audio(audio_path)
            
            # Load and process B-roll videos
            video_clips = await self._load_broll_videos(broll_paths, audio_clip.duration)
            
            # Create subtitle clips
            subtitle_clips = await self._create_subtitle_clips(subtitle_timings)
            
            # Compose final video
            final_video = await self._compose_final_video(
                video_clips, audio_clip, subtitle_clips
            )
            
            # Export video
            await self._export_video(final_video, output_path)
            
            # Clean up
            final_video.close()
            audio_clip.close()
            for clip in video_clips:
                clip.close()
            
            self.logger.info(f"Video composition completed: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Video composition failed: {e}")
            raise
    
    @retry(max_attempts=3, delay=2.0)
    async def _load_audio(self, audio_path: str) -> AudioFileClip:
        """Load audio file."""
        
        if not Path(audio_path).exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        try:
            audio_clip = AudioFileClip(audio_path)
            return audio_clip
        except Exception as e:
            self.logger.error(f"Failed to load audio: {e}")
            raise
    
    async def _load_broll_videos(
        self, 
        broll_paths: List[str], 
        target_duration: float
    ) -> List[VideoFileClip]:
        """Load and process B-roll videos."""
        
        video_clips = []
        
        for broll_path in broll_paths:
            try:
                if not Path(broll_path).exists():
                    self.logger.warning(f"B-roll file not found: {broll_path}")
                    continue
                
                # Load video clip
                video_clip = VideoFileClip(broll_path)
                
                # Resize to target dimensions
                video_clip = video_clip.resize((self.width, self.height))
                
                # Crop to fit aspect ratio if needed
                video_clip = self._crop_to_aspect_ratio(video_clip)
                
                video_clips.append(video_clip)
                
            except Exception as e:
                self.logger.error(f"Failed to load B-roll video {broll_path}: {e}")
        
        return video_clips
    
    def _crop_to_aspect_ratio(self, video_clip: VideoFileClip) -> VideoFileClip:
        """Crop video to target aspect ratio."""
        
        target_aspect = self.width / self.height
        current_aspect = video_clip.w / video_clip.h
        
        if abs(current_aspect - target_aspect) < 0.01:
            return video_clip
        
        if current_aspect > target_aspect:
            # Video is too wide, crop width
            new_width = int(video_clip.h * target_aspect)
            x_center = video_clip.w / 2
            x1 = int(x_center - new_width / 2)
            x2 = int(x_center + new_width / 2)
            return video_clip.crop(x1=x1, x2=x2)
        else:
            # Video is too tall, crop height
            new_height = int(video_clip.w / target_aspect)
            y_center = video_clip.h / 2
            y1 = int(y_center - new_height / 2)
            y2 = int(y_center + new_height / 2)
            return video_clip.crop(y1=y1, y2=y2)
    
    async def _create_subtitle_clips(
        self, 
        subtitle_timings: List[Dict[str, Any]]
    ) -> List[TextClip]:
        """Create subtitle clips from timing data."""
        
        subtitle_clips = []
        
        for subtitle in subtitle_timings:
            try:
                text = subtitle['text']
                start_time = subtitle['start_time']
                end_time = subtitle['end_time']
                
                # Create text clip
                text_clip = TextClip(
                    text,
                    fontsize=48,
                    color='white',
                    font='Arial-Bold',
                    stroke_color='black',
                    stroke_width=2
                ).set_start(start_time).set_end(end_time)
                
                # Position subtitle at bottom of screen
                text_clip = text_clip.set_position(('center', self.height - 150))
                
                subtitle_clips.append(text_clip)
                
            except Exception as e:
                self.logger.error(f"Failed to create subtitle clip: {e}")
        
        return subtitle_clips
    
    async def _compose_final_video(
        self,
        video_clips: List[VideoFileClip],
        audio_clip: AudioFileClip,
        subtitle_clips: List[TextClip]
    ) -> CompositeVideoClip:
        """Compose the final video."""
        
        try:
            # Create background video by looping B-roll clips
            background_video = await self._create_background_video(
                video_clips, audio_clip.duration
            )
            
            # Create composite video with subtitles
            final_video = CompositeVideoClip([
                background_video,
                *subtitle_clips
            ])
            
            # Set audio
            final_video = final_video.set_audio(audio_clip)
            
            # Set duration
            final_video = final_video.set_duration(audio_clip.duration)
            
            return final_video
            
        except Exception as e:
            self.logger.error(f"Failed to compose final video: {e}")
            raise
    
    async def _create_background_video(
        self, 
        video_clips: List[VideoFileClip], 
        target_duration: float
    ) -> VideoFileClip:
        """Create background video by looping B-roll clips."""
        
        if not video_clips:
            # Create a simple colored background if no B-roll available
            from moviepy.editor import ColorClip
            return ColorClip(
                size=(self.width, self.height),
                color=(0, 0, 0),
                duration=target_duration
            )
        
        # Calculate how many times we need to loop each clip
        total_duration = sum(clip.duration for clip in video_clips)
        loops_needed = int(target_duration / total_duration) + 1
        
        # Create looped clips
        looped_clips = []
        for clip in video_clips:
            for _ in range(loops_needed):
                looped_clips.append(clip)
        
        # Concatenate clips
        background_video = concatenate_videoclips(looped_clips)
        
        # Trim to target duration
        background_video = background_video.subclip(0, target_duration)
        
        return background_video
    
    @retry(max_attempts=3, delay=2.0)
    async def _export_video(self, video_clip: CompositeVideoClip, output_path: str) -> None:
        """Export video to file."""
        
        try:
            # Ensure output directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Export video
            video_clip.write_videofile(
                output_path,
                fps=self.fps,
                bitrate=self.bitrate,
                audio_codec='aac',
                audio_bitrate=self.audio_bitrate,
                verbose=False,
                logger=None
            )
            
        except Exception as e:
            self.logger.error(f"Failed to export video: {e}")
            raise
    
    async def add_intro_outro(
        self, 
        video_path: str, 
        intro_path: Optional[str] = None,
        outro_path: Optional[str] = None
    ) -> str:
        """Add intro and outro to video."""
        
        try:
            # Load main video
            main_video = VideoFileClip(video_path)
            
            clips = []
            
            # Add intro if provided
            if intro_path and Path(intro_path).exists():
                intro_clip = VideoFileClip(intro_path)
                intro_clip = intro_clip.resize((self.width, self.height))
                clips.append(intro_clip)
            
            # Add main video
            clips.append(main_video)
            
            # Add outro if provided
            if outro_path and Path(outro_path).exists():
                outro_clip = VideoFileClip(outro_path)
                outro_clip = outro_clip.resize((self.width, self.height))
                clips.append(outro_clip)
            
            # Concatenate clips
            final_video = concatenate_videoclips(clips)
            
            # Generate output filename
            output_filename = f"video_with_intro_outro_{int(asyncio.get_event_loop().time())}.{self.format}"
            output_path = get_output_path(self.config, output_filename)
            
            # Export video
            await self._export_video(final_video, output_path)
            
            # Clean up
            final_video.close()
            main_video.close()
            if intro_path and Path(intro_path).exists():
                intro_clip.close()
            if outro_path and Path(outro_path).exists():
                outro_clip.close()
            
            return output_path
            
        except Exception as e:
            self.logger.error(f"Failed to add intro/outro: {e}")
            raise
    
    async def validate_video_file(self, video_path: str) -> bool:
        """Validate that the composed video file is valid."""
        
        try:
            if not Path(video_path).exists():
                return False
            
            # Check file size (should be > 0)
            file_size = Path(video_path).stat().st_size
            if file_size == 0:
                return False
            
            # Try to load video to check if it's valid
            video_clip = VideoFileClip(video_path)
            duration = video_clip.duration
            video_clip.close()
            
            return duration > 0
            
        except Exception as e:
            self.logger.error(f"Video validation failed: {e}")
            return False

