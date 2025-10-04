"""
B-roll footage downloader using Pexels API.
"""

import asyncio
import os
import requests
from typing import List, Dict, Any, Optional
from pathlib import Path
from urllib.parse import urlencode

from utils.logger import get_logger
from utils.io import get_output_path
from utils.retry import retry


class PexelsBrollDownloader:
    """Handles downloading B-roll footage from Pexels."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_logger("broll_downloader")
        
        # Get API key
        self.api_key = os.getenv("PEXELS_API_KEY")
        if not self.api_key:
            raise ValueError("Pexels API key not found in environment variables")
        
        # Configuration
        self.base_url = "https://api.pexels.com/videos"
        self.per_page = 10
        self.min_duration = 10  # Minimum video duration in seconds
        self.max_duration = 60  # Maximum video duration in seconds
        
        # Video settings
        video_config = config.get("video", {})
        self.width = video_config.get("resolution", {}).get("width", 1080)
        self.height = video_config.get("resolution", {}).get("height", 1920)
    
    async def download_footage(
        self, 
        keywords: List[str], 
        duration: int,
        max_videos: int = 5
    ) -> List[str]:
        """Download B-roll footage for given keywords."""
        
        if not keywords:
            self.logger.warning("No keywords provided for B-roll search")
            return []
        
        downloaded_paths = []
        
        for keyword in keywords[:3]:  # Limit to first 3 keywords
            try:
                videos = await self._search_videos(keyword)
                if not videos:
                    continue
                
                # Select videos that fit our duration requirements
                suitable_videos = self._filter_videos_by_duration(videos, duration)
                
                # Download videos
                for video in suitable_videos[:max_videos]:
                    try:
                        video_path = await self._download_video(video, keyword)
                        if video_path:
                            downloaded_paths.append(video_path)
                    except Exception as e:
                        self.logger.error(f"Failed to download video: {e}")
                
                if len(downloaded_paths) >= max_videos:
                    break
                    
            except Exception as e:
                self.logger.error(f"Failed to search for keyword '{keyword}': {e}")
        
        self.logger.info(f"Downloaded {len(downloaded_paths)} B-roll videos")
        return downloaded_paths
    
    @retry(max_attempts=3, delay=2.0)
    async def _search_videos(self, keyword: str) -> List[Dict[str, Any]]:
        """Search for videos on Pexels."""
        
        params = {
            'query': keyword,
            'per_page': self.per_page,
            'orientation': 'portrait',  # For vertical videos
            'size': 'large'
        }
        
        headers = {
            'Authorization': self.api_key
        }
        
        url = f"{self.base_url}/search?{urlencode(params)}"
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        return data.get('videos', [])
    
    def _filter_videos_by_duration(
        self, 
        videos: List[Dict[str, Any]], 
        target_duration: int
    ) -> List[Dict[str, Any]]:
        """Filter videos by duration requirements."""
        
        suitable_videos = []
        
        for video in videos:
            video_duration = video.get('duration', 0)
            
            # Check if video duration is suitable
            if self.min_duration <= video_duration <= self.max_duration:
                suitable_videos.append(video)
        
        # Sort by duration (closer to target duration first)
        suitable_videos.sort(key=lambda x: abs(x.get('duration', 0) - target_duration))
        
        return suitable_videos
    
    @retry(max_attempts=3, delay=2.0)
    async def _download_video(self, video: Dict[str, Any], keyword: str) -> Optional[str]:
        """Download a single video."""
        
        try:
            # Get video files
            video_files = video.get('video_files', [])
            if not video_files:
                return None
            
            # Find the best quality video file
            best_file = self._select_best_video_file(video_files)
            if not best_file:
                return None
            
            # Generate filename
            video_id = video.get('id', 'unknown')
            filename = f"broll_{keyword}_{video_id}.mp4"
            output_path = get_output_path(self.config, filename)
            
            # Download video
            await self._download_file(best_file['link'], output_path)
            
            self.logger.info(f"Downloaded B-roll video: {filename}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Failed to download video {video.get('id', 'unknown')}: {e}")
            return None
    
    def _select_best_video_file(self, video_files: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Select the best quality video file."""
        
        # Filter for suitable dimensions
        suitable_files = []
        for file in video_files:
            width = file.get('width', 0)
            height = file.get('height', 0)
            
            # Prefer vertical videos (height > width)
            if height > width and height >= self.height:
                suitable_files.append(file)
        
        if not suitable_files:
            # Fallback to any file if no suitable ones found
            suitable_files = video_files
        
        # Sort by quality (prefer higher resolution)
        suitable_files.sort(key=lambda x: x.get('width', 0) * x.get('height', 0), reverse=True)
        
        return suitable_files[0] if suitable_files else None
    
    async def _download_file(self, url: str, output_path: str) -> None:
        """Download file from URL."""
        
        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Download file
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
    
    async def get_video_info(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific video."""
        
        try:
            headers = {
                'Authorization': self.api_key
            }
            
            url = f"{self.base_url}/videos/{video_id}"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            self.logger.error(f"Failed to get video info for {video_id}: {e}")
            return None
    
    async def cleanup_old_videos(self, max_age_days: int = 7) -> None:
        """Clean up old downloaded videos."""
        
        output_dir = Path(self.config.get("paths", {}).get("outputs", "./data/outputs"))
        
        if not output_dir.exists():
            return
        
        import time
        cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)
        
        for file_path in output_dir.glob("broll_*.mp4"):
            if file_path.stat().st_mtime < cutoff_time:
                file_path.unlink()
                self.logger.info(f"Cleaned up old B-roll video: {file_path.name}")
    
    async def validate_video_file(self, video_path: str) -> bool:
        """Validate that the downloaded video file is valid."""
        
        try:
            if not Path(video_path).exists():
                return False
            
            # Check file size (should be > 0)
            file_size = Path(video_path).stat().st_size
            if file_size == 0:
                return False
            
            # Basic validation - file exists and has content
            return True
            
        except Exception as e:
            self.logger.error(f"Video validation failed: {e}")
            return False

