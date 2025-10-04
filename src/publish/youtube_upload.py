"""
YouTube upload module for publishing videos to YouTube.
"""

import asyncio
import os
import json
from typing import Dict, Any, Optional, List
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from utils.logger import get_logger
from utils.io import load_json, save_json
from utils.hash import generate_content_hash, check_duplicate_content, save_content_hash
from utils.retry import retry


class YouTubeUploader:
    """Handles YouTube video uploads and management."""
    
    # YouTube API scopes
    SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_logger("youtube_uploader")
        
        # YouTube settings
        youtube_config = config.get("youtube", {})
        self.privacy_status = youtube_config.get("privacy_status", "private")
        self.category_id = youtube_config.get("category_id", "25")  # News & Politics
        self.default_language = youtube_config.get("default_language", "en")
        self.default_tags = youtube_config.get("tags", [])
        
        # OAuth paths
        oauth_dir = config.get("paths", {}).get("oauth", "./yt_oauth")
        self.client_secret_path = os.path.join(oauth_dir, "client_secret.json")
        self.token_path = os.path.join(oauth_dir, "token.json")
        
        # Initialize YouTube service
        self.youtube_service = None
        self._initialize_service()
    
    def _initialize_service(self) -> None:
        """Initialize YouTube API service."""
        
        try:
            creds = self._get_credentials()
            self.youtube_service = build('youtube', 'v3', credentials=creds)
            self.logger.info("YouTube API service initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize YouTube service: {e}")
            raise
    
    def _get_credentials(self) -> Credentials:
        """Get or refresh YouTube API credentials."""
        
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, self.SCOPES)
        
        # If there are no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    self.logger.error(f"Failed to refresh credentials: {e}")
                    creds = None
            
            if not creds:
                if not os.path.exists(self.client_secret_path):
                    raise FileNotFoundError(
                        f"Client secret file not found: {self.client_secret_path}\n"
                        "Please download your OAuth2 client secret from Google Cloud Console."
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.client_secret_path, self.SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            os.makedirs(os.path.dirname(self.token_path), exist_ok=True)
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())
        
        return creds
    
    async def upload_video(
        self,
        video_path: str,
        thumbnail_path: str,
        script: Dict[str, Any],
        custom_title: Optional[str] = None,
        custom_description: Optional[str] = None,
        custom_tags: Optional[List[str]] = None
    ) -> str:
        """Upload video to YouTube."""
        
        try:
            # Check for duplicate content
            content_hash = generate_content_hash(f"{script['title']}|{script['content']}")
            hash_file = "./data/logs/youtube_uploads.txt"
            
            if check_duplicate_content(content_hash, hash_file):
                self.logger.warning(f"Skipping duplicate upload: {script['title'][:50]}...")
                return None
            
            # Prepare video metadata
            video_metadata = self._prepare_video_metadata(
                script, custom_title, custom_description, custom_tags
            )
            
            # Upload video
            video_id = await self._upload_video_file(video_path, video_metadata)
            
            # Upload thumbnail
            if thumbnail_path and os.path.exists(thumbnail_path):
                await self._upload_thumbnail(video_id, thumbnail_path)
            
            # Save upload record
            save_content_hash(content_hash, hash_file, {
                'timestamp': asyncio.get_event_loop().time(),
                'title': script['title'],
                'video_id': video_id,
                'url': f"https://www.youtube.com/watch?v={video_id}"
            })
            
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            self.logger.info(f"Video uploaded successfully: {video_url}")
            
            return video_url
            
        except Exception as e:
            self.logger.error(f"Video upload failed: {e}")
            raise
    
    def _prepare_video_metadata(
        self,
        script: Dict[str, Any],
        custom_title: Optional[str] = None,
        custom_description: Optional[str] = None,
        custom_tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Prepare video metadata for upload."""
        
        # Use custom title or generate from script
        title = custom_title or script.get('title', 'Finance News Update')
        
        # Limit title length (YouTube limit is 100 characters)
        if len(title) > 100:
            title = title[:97] + "..."
        
        # Generate description
        description = custom_description or self._generate_description(script)
        
        # Combine tags
        tags = list(set(self.default_tags + script.get('keywords', []) + (custom_tags or [])))
        
        # Limit tags (YouTube limit is 500 characters total)
        tags_text = ', '.join(tags)
        if len(tags_text) > 500:
            # Truncate tags to fit
            tags = tags[:len(tags) // 2]  # Rough approximation
        
        return {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags,
                'categoryId': self.category_id,
                'defaultLanguage': self.default_language
            },
            'status': {
                'privacyStatus': self.privacy_status,
                'selfDeclaredMadeForKids': False
            }
        }
    
    def _generate_description(self, script: Dict[str, Any]) -> str:
        """Generate video description from script."""
        
        description_parts = []
        
        # Add hook
        if script.get('hook'):
            description_parts.append(script['hook'])
            description_parts.append("")
        
        # Add main content (truncated)
        content = script.get('content', '')
        if content:
            # Limit content length
            max_content_length = 1000
            if len(content) > max_content_length:
                content = content[:max_content_length] + "..."
            description_parts.append(content)
            description_parts.append("")
        
        # Add CTA
        if script.get('cta'):
            description_parts.append(script['cta'])
            description_parts.append("")
        
        # Add hashtags
        keywords = script.get('keywords', [])
        if keywords:
            hashtags = ' '.join([f"#{keyword.replace(' ', '')}" for keyword in keywords[:5]])
            description_parts.append(hashtags)
        
        # Add standard footer
        description_parts.extend([
            "",
            "🔔 Subscribe for daily finance updates!",
            "📈 Follow us for market insights and analysis",
            "",
            "#Finance #News #Investing #Markets #AI"
        ])
        
        return '\n'.join(description_parts)
    
    @retry(max_attempts=3, delay=5.0)
    async def _upload_video_file(
        self, 
        video_path: str, 
        video_metadata: Dict[str, Any]
    ) -> str:
        """Upload video file to YouTube."""
        
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        try:
            # Create media upload
            media = MediaFileUpload(
                video_path,
                chunksize=-1,
                resumable=True,
                mimetype='video/mp4'
            )
            
            # Insert video
            insert_request = self.youtube_service.videos().insert(
                part=','.join(video_metadata.keys()),
                body=video_metadata,
                media_body=media
            )
            
            # Execute upload
            response = None
            while response is None:
                status, response = insert_request.next_chunk()
                if status:
                    self.logger.info(f"Upload progress: {int(status.progress() * 100)}%")
            
            if 'id' in response:
                return response['id']
            else:
                raise Exception(f"Upload failed: {response}")
                
        except HttpError as e:
            self.logger.error(f"YouTube API error: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Upload error: {e}")
            raise
    
    @retry(max_attempts=3, delay=2.0)
    async def _upload_thumbnail(self, video_id: str, thumbnail_path: str) -> None:
        """Upload thumbnail for video."""
        
        if not os.path.exists(thumbnail_path):
            self.logger.warning(f"Thumbnail file not found: {thumbnail_path}")
            return
        
        try:
            self.youtube_service.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path)
            ).execute()
            
            self.logger.info(f"Thumbnail uploaded for video: {video_id}")
            
        except HttpError as e:
            self.logger.error(f"Thumbnail upload failed: {e}")
            raise
    
    async def update_video_metadata(
        self,
        video_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        privacy_status: Optional[str] = None
    ) -> bool:
        """Update video metadata."""
        
        try:
            # Get current video data
            video_response = self.youtube_service.videos().list(
                part='snippet,status',
                id=video_id
            ).execute()
            
            if not video_response['items']:
                self.logger.error(f"Video not found: {video_id}")
                return False
            
            video = video_response['items'][0]
            
            # Update metadata
            if title:
                video['snippet']['title'] = title
            if description:
                video['snippet']['description'] = description
            if tags:
                video['snippet']['tags'] = tags
            if privacy_status:
                video['status']['privacyStatus'] = privacy_status
            
            # Update video
            update_response = self.youtube_service.videos().update(
                part='snippet,status',
                body=video
            ).execute()
            
            self.logger.info(f"Video metadata updated: {video_id}")
            return True
            
        except HttpError as e:
            self.logger.error(f"Failed to update video metadata: {e}")
            return False
    
    async def get_video_info(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Get video information."""
        
        try:
            response = self.youtube_service.videos().list(
                part='snippet,statistics,status',
                id=video_id
            ).execute()
            
            if response['items']:
                return response['items'][0]
            return None
            
        except HttpError as e:
            self.logger.error(f"Failed to get video info: {e}")
            return None
    
    async def delete_video(self, video_id: str) -> bool:
        """Delete a video from YouTube."""
        
        try:
            self.youtube_service.videos().delete(id=video_id).execute()
            self.logger.info(f"Video deleted: {video_id}")
            return True
            
        except HttpError as e:
            self.logger.error(f"Failed to delete video: {e}")
            return False
    
    async def list_uploaded_videos(self, max_results: int = 50) -> List[Dict[str, Any]]:
        """List uploaded videos."""
        
        try:
            response = self.youtube_service.videos().list(
                part='snippet,statistics',
                mySubscriptions=False,
                maxResults=max_results,
                order='date'
            ).execute()
            
            return response.get('items', [])
            
        except HttpError as e:
            self.logger.error(f"Failed to list videos: {e}")
            return []

