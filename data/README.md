# Data Directory Structure

## workitems/
This directory contains work items (JSON files) that are waiting to be processed.
Each work item represents a news article that needs to be converted into a video.

**File format:** `workitem_YYYYMMDD_HHMMSS_<hash>.json`

## outputs/
This directory contains the generated outputs organized by date:
- `YYYY-MM-DD/` - Daily output folders
  - `audio/` - Generated audio files (.mp3)
  - `video/` - Composed video files (.mp4)
  - `thumbnails/` - Generated thumbnail images (.jpg)
  - `metadata/` - Video metadata and scripts (.json)

## logs/
This directory contains log files:
- `pipeline.log` - Main pipeline logs
- `news_ingester.log` - News feed ingestion logs
- `script_writer.log` - Script generation logs
- `tts.log` - Text-to-speech logs
- `video_composer.log` - Video composition logs
- `youtube_uploader.log` - YouTube upload logs
- `content_hashes_*.txt` - Content hash files for duplicate detection
- `script_hashes.txt` - Script hash files for duplicate detection
- `youtube_uploads.txt` - YouTube upload records

## File Cleanup

Old files are automatically cleaned up based on the configuration:
- Default retention: 7 days
- Configurable in `config.yaml` under `pipeline.cleanup_old_files_days`

