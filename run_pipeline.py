#!/usr/bin/env python3
"""
YouTube AI Finance Pipeline - Main Entry Point

This script orchestrates the entire pipeline from news ingestion to YouTube upload.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any

import yaml
from dotenv import load_dotenv

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

from utils.logger import setup_logger
from utils.io import load_config, ensure_directories
from ingest.news_feed import NewsFeedIngester
from author.script_writer import ScriptWriter
from voice.tts_elevenlabs import ElevenLabsTTS
from media.broll_pexels import PexelsBrollDownloader
from media.compose_moviepy import VideoComposer
from media.thumbnail import ThumbnailGenerator
from publish.youtube_upload import YouTubeUploader


class YouTubeAIPipeline:
    """Main pipeline orchestrator for YouTube AI Finance content generation."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the pipeline with configuration."""
        load_dotenv()
        self.config = load_config(config_path)
        self.logger = setup_logger("pipeline", self.config)
        
        # Initialize components
        self.news_ingester = NewsFeedIngester(self.config)
        self.script_writer = ScriptWriter(self.config)
        self.tts = ElevenLabsTTS(self.config)
        self.broll_downloader = PexelsBrollDownloader(self.config)
        self.video_composer = VideoComposer(self.config)
        self.thumbnail_generator = ThumbnailGenerator(self.config)
        self.youtube_uploader = YouTubeUploader(self.config)
        
        # Ensure directories exist
        ensure_directories(self.config)
        
    async def run_pipeline(self) -> None:
        """Run the complete pipeline."""
        try:
            self.logger.info("Starting YouTube AI Finance Pipeline")
            
            # Step 1: Ingest news and create work items
            work_items = await self.ingest_news()
            if not work_items:
                self.logger.warning("No work items created, pipeline stopping")
                return
                
            # Step 2: Process each work item
            for work_item in work_items:
                await self.process_work_item(work_item)
                
            self.logger.info("Pipeline completed successfully")
            
        except Exception as e:
            self.logger.error(f"Pipeline failed: {e}", exc_info=True)
            raise
    
    async def ingest_news(self) -> List[Dict[str, Any]]:
        """Ingest news feeds and create work items."""
        self.logger.info("Ingesting news feeds...")
        
        news_items = await self.news_ingester.fetch_news()
        work_items = []
        
        for news_item in news_items:
            work_item = {
                "id": news_item["id"],
                "title": news_item["title"],
                "summary": news_item["summary"],
                "keywords": news_item["keywords"],
                "source": news_item["source"],
                "timestamp": news_item["timestamp"],
                "status": "pending"
            }
            work_items.append(work_item)
            
        self.logger.info(f"Created {len(work_items)} work items")
        return work_items
    
    async def process_work_item(self, work_item: Dict[str, Any]) -> None:
        """Process a single work item through the entire pipeline."""
        work_item_id = work_item["id"]
        self.logger.info(f"Processing work item: {work_item_id}")
        
        try:
            # Step 1: Generate script
            script = await self.script_writer.generate_script(work_item)
            work_item["script"] = script
            work_item["status"] = "script_generated"
            
            # Step 2: Generate audio
            audio_path = await self.tts.generate_audio(script["content"])
            work_item["audio_path"] = audio_path
            work_item["status"] = "audio_generated"
            
            # Step 3: Download B-roll footage
            broll_paths = await self.broll_downloader.download_footage(
                script["keywords"], script["duration"]
            )
            work_item["broll_paths"] = broll_paths
            work_item["status"] = "broll_downloaded"
            
            # Step 4: Compose video
            video_path = await self.video_composer.compose_video(
                audio_path, broll_paths, script["subtitle_timings"]
            )
            work_item["video_path"] = video_path
            work_item["status"] = "video_composed"
            
            # Step 5: Generate thumbnail
            thumbnail_path = await self.thumbnail_generator.generate_thumbnail(
                work_item["title"], script["keywords"]
            )
            work_item["thumbnail_path"] = thumbnail_path
            work_item["status"] = "thumbnail_generated"
            
            # Step 6: Upload to YouTube
            youtube_url = await self.youtube_uploader.upload_video(
                video_path, thumbnail_path, script
            )
            work_item["youtube_url"] = youtube_url
            work_item["status"] = "uploaded"
            
            self.logger.info(f"Successfully processed work item: {work_item_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to process work item {work_item_id}: {e}")
            work_item["status"] = "failed"
            work_item["error"] = str(e)


async def main():
    """Main entry point."""
    pipeline = YouTubeAIPipeline()
    await pipeline.run_pipeline()


if __name__ == "__main__":
    asyncio.run(main())

