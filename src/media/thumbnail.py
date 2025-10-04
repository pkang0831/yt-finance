"""
Thumbnail generation module for creating YouTube thumbnails.
"""

import asyncio
import os
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import textwrap

from utils.logger import get_logger
from utils.io import get_output_path
from utils.retry import retry


class ThumbnailGenerator:
    """Handles thumbnail generation for YouTube videos."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_logger("thumbnail_generator")
        
        # Thumbnail settings
        thumbnail_config = config.get("thumbnail", {})
        self.width = thumbnail_config.get("width", 1280)
        self.height = thumbnail_config.get("height", 720)
        self.format = thumbnail_config.get("format", "jpg")
        self.quality = thumbnail_config.get("quality", 95)
        
        # Design settings
        self.background_color = (20, 20, 30)  # Dark blue-gray
        self.text_color = (255, 255, 255)  # White
        self.accent_color = (255, 215, 0)  # Gold
        self.font_size_large = 72
        self.font_size_medium = 48
        self.font_size_small = 32
    
    async def generate_thumbnail(
        self,
        title: str,
        keywords: List[str],
        output_filename: Optional[str] = None
    ) -> str:
        """Generate a thumbnail for the video."""
        
        if not output_filename:
            timestamp = asyncio.get_event_loop().time()
            output_filename = f"thumbnail_{int(timestamp)}.{self.format}"
        
        output_path = get_output_path(self.config, output_filename)
        
        try:
            self.logger.info(f"Generating thumbnail for: {title[:50]}...")
            
            # Create base image
            thumbnail = await self._create_base_image()
            
            # Add background pattern
            thumbnail = await self._add_background_pattern(thumbnail)
            
            # Add title text
            thumbnail = await self._add_title_text(thumbnail, title)
            
            # Add keywords as tags
            thumbnail = await self._add_keyword_tags(thumbnail, keywords)
            
            # Add visual elements
            thumbnail = await self._add_visual_elements(thumbnail)
            
            # Apply final effects
            thumbnail = await self._apply_final_effects(thumbnail)
            
            # Save thumbnail
            await self._save_thumbnail(thumbnail, output_path)
            
            self.logger.info(f"Thumbnail generated: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Thumbnail generation failed: {e}")
            raise
    
    async def _create_base_image(self) -> Image.Image:
        """Create base thumbnail image."""
        
        # Create image with background color
        image = Image.new('RGB', (self.width, self.height), self.background_color)
        return image
    
    async def _add_background_pattern(self, image: Image.Image) -> Image.Image:
        """Add background pattern to image."""
        
        # Create a subtle gradient effect
        draw = ImageDraw.Draw(image)
        
        # Add gradient from top to bottom
        for y in range(self.height):
            # Calculate color intensity based on position
            intensity = int(255 * (1 - y / self.height) * 0.1)
            color = (
                self.background_color[0] + intensity,
                self.background_color[1] + intensity,
                self.background_color[2] + intensity
            )
            draw.line([(0, y), (self.width, y)], fill=color)
        
        return image
    
    async def _add_title_text(self, image: Image.Image, title: str) -> Image.Image:
        """Add title text to thumbnail."""
        
        try:
            # Load font (fallback to default if not available)
            try:
                font = ImageFont.truetype("arial.ttf", self.font_size_large)
            except OSError:
                font = ImageFont.load_default()
            
            # Wrap text to fit thumbnail
            max_chars_per_line = 25
            wrapped_text = textwrap.fill(title, max_chars_per_line)
            lines = wrapped_text.split('\n')
            
            # Calculate text position
            line_height = self.font_size_large + 10
            total_height = len(lines) * line_height
            start_y = (self.height - total_height) // 2
            
            draw = ImageDraw.Draw(image)
            
            # Add text with outline
            for i, line in enumerate(lines):
                y_pos = start_y + i * line_height
                
                # Draw text outline (black)
                for dx in [-2, -1, 0, 1, 2]:
                    for dy in [-2, -1, 0, 1, 2]:
                        if dx != 0 or dy != 0:
                            draw.text(
                                (self.width // 2 + dx, y_pos + dy),
                                line,
                                font=font,
                                fill=(0, 0, 0),
                                anchor="mm"
                            )
                
                # Draw main text (white)
                draw.text(
                    (self.width // 2, y_pos),
                    line,
                    font=font,
                    fill=self.text_color,
                    anchor="mm"
                )
            
            return image
            
        except Exception as e:
            self.logger.error(f"Failed to add title text: {e}")
            return image
    
    async def _add_keyword_tags(self, image: Image.Image, keywords: List[str]) -> Image.Image:
        """Add keyword tags to thumbnail."""
        
        if not keywords:
            return image
        
        try:
            # Load font for tags
            try:
                font = ImageFont.truetype("arial.ttf", self.font_size_small)
            except OSError:
                font = ImageFont.load_default()
            
            draw = ImageDraw.Draw(image)
            
            # Position tags at bottom of image
            tag_y = self.height - 80
            tag_spacing = 20
            tag_height = 40
            
            # Calculate total width needed
            total_width = sum(len(keyword) * 12 + 20 for keyword in keywords[:3])  # Limit to 3 keywords
            start_x = (self.width - total_width) // 2
            
            current_x = start_x
            
            for keyword in keywords[:3]:  # Limit to 3 keywords
                # Create tag background
                tag_width = len(keyword) * 12 + 20
                
                # Draw tag background
                draw.rounded_rectangle(
                    [current_x, tag_y, current_x + tag_width, tag_y + tag_height],
                    radius=10,
                    fill=self.accent_color
                )
                
                # Draw tag text
                draw.text(
                    (current_x + tag_width // 2, tag_y + tag_height // 2),
                    keyword.upper(),
                    font=font,
                    fill=(0, 0, 0),  # Black text on gold background
                    anchor="mm"
                )
                
                current_x += tag_width + tag_spacing
            
            return image
            
        except Exception as e:
            self.logger.error(f"Failed to add keyword tags: {e}")
            return image
    
    async def _add_visual_elements(self, image: Image.Image) -> Image.Image:
        """Add visual elements to thumbnail."""
        
        try:
            draw = ImageDraw.Draw(image)
            
            # Add corner accents
            corner_size = 50
            
            # Top-left corner
            draw.polygon(
                [(0, 0), (corner_size, 0), (0, corner_size)],
                fill=self.accent_color
            )
            
            # Top-right corner
            draw.polygon(
                [(self.width, 0), (self.width - corner_size, 0), (self.width, corner_size)],
                fill=self.accent_color
            )
            
            # Add a subtle border
            border_width = 4
            draw.rectangle(
                [0, 0, self.width, self.height],
                outline=self.accent_color,
                width=border_width
            )
            
            return image
            
        except Exception as e:
            self.logger.error(f"Failed to add visual elements: {e}")
            return image
    
    async def _apply_final_effects(self, image: Image.Image) -> Image.Image:
        """Apply final effects to thumbnail."""
        
        try:
            # Enhance contrast slightly
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.1)
            
            # Enhance sharpness
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.2)
            
            # Apply subtle blur to background
            # This is a simple effect - in production, you might want more sophisticated effects
            
            return image
            
        except Exception as e:
            self.logger.error(f"Failed to apply final effects: {e}")
            return image
    
    async def _save_thumbnail(self, image: Image.Image, output_path: str) -> None:
        """Save thumbnail to file."""
        
        try:
            # Ensure output directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Save image
            if self.format.lower() == 'jpg' or self.format.lower() == 'jpeg':
                image.save(output_path, 'JPEG', quality=self.quality, optimize=True)
            elif self.format.lower() == 'png':
                image.save(output_path, 'PNG', optimize=True)
            else:
                image.save(output_path, 'JPEG', quality=self.quality, optimize=True)
            
        except Exception as e:
            self.logger.error(f"Failed to save thumbnail: {e}")
            raise
    
    async def create_thumbnail_with_image(
        self,
        title: str,
        keywords: List[str],
        background_image_path: str,
        output_filename: Optional[str] = None
    ) -> str:
        """Create thumbnail using a background image."""
        
        if not output_filename:
            timestamp = asyncio.get_event_loop().time()
            output_filename = f"thumbnail_with_bg_{int(timestamp)}.{self.format}"
        
        output_path = get_output_path(self.config, output_filename)
        
        try:
            # Load background image
            background = Image.open(background_image_path)
            background = background.resize((self.width, self.height), Image.Resampling.LANCZOS)
            
            # Apply overlay
            overlay = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 100))
            background = Image.alpha_composite(background.convert('RGBA'), overlay)
            background = background.convert('RGB')
            
            # Add title text
            thumbnail = await self._add_title_text(background, title)
            
            # Add keyword tags
            thumbnail = await self._add_keyword_tags(thumbnail, keywords)
            
            # Add visual elements
            thumbnail = await self._add_visual_elements(thumbnail)
            
            # Apply final effects
            thumbnail = await self._apply_final_effects(thumbnail)
            
            # Save thumbnail
            await self._save_thumbnail(thumbnail, output_path)
            
            self.logger.info(f"Thumbnail with background generated: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Thumbnail with background generation failed: {e}")
            raise
    
    async def validate_thumbnail_file(self, thumbnail_path: str) -> bool:
        """Validate that the generated thumbnail file is valid."""
        
        try:
            if not Path(thumbnail_path).exists():
                return False
            
            # Check file size (should be > 0)
            file_size = Path(thumbnail_path).stat().st_size
            if file_size == 0:
                return False
            
            # Try to load image to check if it's valid
            image = Image.open(thumbnail_path)
            width, height = image.size
            image.close()
            
            return width > 0 and height > 0
            
        except Exception as e:
            self.logger.error(f"Thumbnail validation failed: {e}")
            return False

