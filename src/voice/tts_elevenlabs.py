"""
Text-to-speech module using ElevenLabs API.
"""

import asyncio
import os
from typing import Dict, Any, Optional
from pathlib import Path

import requests
from elevenlabs import Voice, VoiceSettings, generate, save

from utils.logger import get_logger
from utils.io import get_output_path
from utils.retry import retry


class ElevenLabsTTS:
    """Handles text-to-speech generation using ElevenLabs API."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_logger("tts")
        
        # Get API key
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            raise ValueError("ElevenLabs API key not found in environment variables")
        
        # Set API key
        os.environ["ELEVENLABS_API_KEY"] = api_key
        
        # Configuration
        self.voice_id = os.getenv("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB")  # Default voice
        self.model_id = os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")
        
        # Voice settings
        voice_settings = config.get("ai_models", {}).get("elevenlabs", {}).get("voice_settings", {})
        self.stability = voice_settings.get("stability", 0.5)
        self.similarity_boost = voice_settings.get("similarity_boost", 0.75)
        
        # Audio settings
        audio_config = config.get("audio", {})
        self.sample_rate = audio_config.get("sample_rate", 44100)
        self.bitrate = audio_config.get("bitrate", "128k")
        self.format = audio_config.get("format", "mp3")
    
    async def generate_audio(self, text: str, output_filename: Optional[str] = None) -> str:
        """Generate audio from text using ElevenLabs TTS."""
        
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        # Generate output filename if not provided
        if not output_filename:
            timestamp = asyncio.get_event_loop().time()
            output_filename = f"audio_{int(timestamp)}.{self.format}"
        
        # Get full output path
        output_path = get_output_path(self.config, output_filename)
        
        try:
            self.logger.info(f"Generating audio for text: {text[:100]}...")
            
            # Generate audio
            audio_data = await self._generate_audio_data(text)
            
            # Save audio file
            await self._save_audio_file(audio_data, output_path)
            
            self.logger.info(f"Audio generated successfully: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Failed to generate audio: {e}")
            raise
    
    @retry(max_attempts=3, delay=2.0)
    async def _generate_audio_data(self, text: str) -> bytes:
        """Generate audio data from text."""
        
        try:
            # Create voice settings
            voice_settings = VoiceSettings(
                stability=self.stability,
                similarity_boost=self.similarity_boost
            )
            
            # Generate audio
            audio_data = generate(
                text=text,
                voice=Voice(
                    voice_id=self.voice_id,
                    settings=voice_settings
                ),
                model=self.model_id
            )
            
            return audio_data
            
        except Exception as e:
            self.logger.error(f"ElevenLabs API error: {e}")
            raise
    
    async def _save_audio_file(self, audio_data: bytes, output_path: str) -> None:
        """Save audio data to file."""
        
        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Save audio file
        with open(output_path, 'wb') as f:
            f.write(audio_data)
    
    async def get_available_voices(self) -> list:
        """Get list of available voices."""
        
        try:
            response = requests.get(
                "https://api.elevenlabs.io/v1/voices",
                headers={"xi-api-key": os.getenv("ELEVENLABS_API_KEY")}
            )
            response.raise_for_status()
            
            voices_data = response.json()
            return voices_data.get("voices", [])
            
        except Exception as e:
            self.logger.error(f"Failed to get available voices: {e}")
            return []
    
    async def test_voice(self, voice_id: str, test_text: str = "Hello, this is a test of the voice.") -> bool:
        """Test a voice with sample text."""
        
        try:
            original_voice_id = self.voice_id
            self.voice_id = voice_id
            
            audio_data = await self._generate_audio_data(test_text)
            
            # Restore original voice ID
            self.voice_id = original_voice_id
            
            return len(audio_data) > 0
            
        except Exception as e:
            self.logger.error(f"Voice test failed: {e}")
            return False
    
    async def optimize_text_for_tts(self, text: str) -> str:
        """Optimize text for better TTS output."""
        
        # Remove extra whitespace
        text = " ".join(text.split())
        
        # Add pauses for better pacing
        text = text.replace(".", ". ")
        text = text.replace(",", ", ")
        text = text.replace(":", ": ")
        text = text.replace(";", "; ")
        
        # Handle numbers and currency
        text = text.replace("$", "dollars ")
        text = text.replace("%", "percent ")
        
        # Clean up multiple spaces
        text = " ".join(text.split())
        
        return text
    
    async def generate_audio_with_timing(self, script: Dict[str, Any]) -> Dict[str, Any]:
        """Generate audio with timing information for subtitles."""
        
        # Get optimized text
        optimized_text = await self.optimize_text_for_tts(script.get('optimized_content', script['content']))
        
        # Generate audio
        audio_path = await self.generate_audio(optimized_text)
        
        # Estimate timing based on text length
        word_count = len(optimized_text.split())
        estimated_duration = (word_count / 200) * 60  # 200 words per minute
        
        return {
            'audio_path': audio_path,
            'duration': estimated_duration,
            'word_count': word_count,
            'text': optimized_text
        }
    
    async def validate_audio_file(self, audio_path: str) -> bool:
        """Validate that the generated audio file is valid."""
        
        try:
            if not Path(audio_path).exists():
                return False
            
            # Check file size (should be > 0)
            file_size = Path(audio_path).stat().st_size
            if file_size == 0:
                return False
            
            # Basic validation - file exists and has content
            return True
            
        except Exception as e:
            self.logger.error(f"Audio validation failed: {e}")
            return False

