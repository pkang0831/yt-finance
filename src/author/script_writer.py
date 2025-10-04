"""
Script writer module for generating video scripts using LLM.
"""

import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

import openai
from openai import AsyncOpenAI

from utils.logger import get_logger
from utils.text import clean_text, truncate_text, create_hook, extract_sentences
from utils.hash import generate_script_hash, check_duplicate_content, save_content_hash
from utils.retry import retry


class ScriptWriter:
    """Handles script generation using OpenAI's GPT models."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_logger("script_writer")
        
        # Initialize OpenAI client
        api_key = config.get("ai_models", {}).get("openai", {}).get("api_key")
        if not api_key:
            import os
            api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            raise ValueError("OpenAI API key not found in config or environment")
        
        self.client = AsyncOpenAI(api_key=api_key)
        
        # Configuration
        self.model = config.get("ai_models", {}).get("openai", {}).get("model", "gpt-4")
        self.temperature = config.get("ai_models", {}).get("openai", {}).get("temperature", 0.7)
        self.max_tokens = config.get("ai_models", {}).get("openai", {}).get("max_tokens", 2000)
        
        # Script settings
        self.script_length = config.get("content", {}).get("script_length_seconds", 60)
        self.hook_duration = config.get("content", {}).get("hook_duration_seconds", 5)
        self.cta_duration = config.get("content", {}).get("cta_duration_seconds", 10)
        self.language = config.get("content", {}).get("language", "en")
        self.tone = config.get("content", {}).get("tone", "professional")
    
    async def generate_script(self, work_item: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a complete script for a work item."""
        
        # Check for duplicate scripts
        script_hash = generate_script_hash({
            'title': work_item['title'],
            'summary': work_item['summary'],
            'keywords': work_item['keywords']
        })
        
        hash_file = f"./data/logs/script_hashes.txt"
        if check_duplicate_content(script_hash, hash_file):
            self.logger.warning(f"Skipping duplicate script for: {work_item['title'][:50]}...")
            return None
        
        try:
            # Generate main script content
            script_content = await self._generate_script_content(work_item)
            
            # Generate hook
            hook = await self._generate_hook(work_item, script_content)
            
            # Generate CTA
            cta = await self._generate_cta(work_item, script_content)
            
            # Generate subtitle timings
            subtitle_timings = await self._generate_subtitle_timings(script_content)
            
            # Create complete script
            script = {
                'id': f"script_{work_item['id']}",
                'work_item_id': work_item['id'],
                'title': work_item['title'],
                'hook': hook,
                'content': script_content,
                'cta': cta,
                'keywords': work_item['keywords'],
                'duration': self.script_length,
                'subtitle_timings': subtitle_timings,
                'language': self.language,
                'tone': self.tone,
                'generated_at': datetime.now().isoformat(),
                'script_hash': script_hash
            }
            
            # Save script hash
            save_content_hash(script_hash, hash_file, {
                'timestamp': datetime.now().isoformat(),
                'title': work_item['title'],
                'work_item_id': work_item['id']
            })
            
            self.logger.info(f"Generated script for: {work_item['title'][:50]}...")
            return script
            
        except Exception as e:
            self.logger.error(f"Failed to generate script for {work_item['title']}: {e}")
            raise
    
    @retry(max_attempts=3, delay=2.0)
    async def _generate_script_content(self, work_item: Dict[str, Any]) -> str:
        """Generate the main script content."""
        
        prompt = f"""
You are a professional finance content creator for YouTube. Create a {self.script_length}-second video script about the following news:

Title: {work_item['title']}
Summary: {work_item['summary']}
Keywords: {', '.join(work_item['keywords'])}

Requirements:
- Duration: Exactly {self.script_length} seconds (approximately {self.script_length * 3} words)
- Tone: {self.tone}
- Language: {self.language}
- Target audience: Finance enthusiasts and investors
- Structure: Clear introduction, main points, conclusion
- Include specific numbers, percentages, or data points when available
- Make it engaging and easy to understand
- Avoid jargon, explain complex terms
- End with a clear takeaway

Format the script as clean text without timestamps or formatting instructions.
"""
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a professional finance content creator with expertise in making complex financial news accessible to general audiences."},
                {"role": "user", "content": prompt}
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )
        
        script_content = response.choices[0].message.content.strip()
        return clean_text(script_content)
    
    @retry(max_attempts=3, delay=2.0)
    async def _generate_hook(self, work_item: Dict[str, Any], script_content: str) -> str:
        """Generate an engaging hook for the video."""
        
        prompt = f"""
Create a compelling hook for a YouTube finance video. The hook should:

- Be {self.hook_duration} seconds long (approximately {self.hook_duration * 3} words)
- Immediately grab attention
- Create curiosity or urgency
- Relate to: {work_item['title']}
- Use a {self.tone} tone
- Be suitable for {self.language} language

Examples of effective hooks:
- "Breaking: This just happened and it's about to change everything..."
- "You won't believe what just happened in the markets..."
- "This shocking development could impact your investments..."

Create a hook that fits the news story and will make viewers want to watch the entire video.
"""
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert at creating compelling video hooks that maximize viewer engagement."},
                {"role": "user", "content": prompt}
            ],
            temperature=self.temperature,
            max_tokens=200
        )
        
        hook = response.choices[0].message.content.strip()
        return clean_text(hook)
    
    @retry(max_attempts=3, delay=2.0)
    async def _generate_cta(self, work_item: Dict[str, Any], script_content: str) -> str:
        """Generate a call-to-action for the video."""
        
        prompt = f"""
Create a compelling call-to-action for a YouTube finance video. The CTA should:

- Be {self.cta_duration} seconds long (approximately {self.cta_duration * 3} words)
- Encourage engagement (like, subscribe, comment)
- Ask viewers to share their thoughts
- Be relevant to the finance topic: {work_item['title']}
- Use a {self.tone} tone
- Be suitable for {self.language} language

Examples of effective CTAs:
- "What do you think about this development? Let me know in the comments below!"
- "If you found this helpful, please like and subscribe for more finance insights!"
- "How will this affect your investment strategy? Share your thoughts!"

Create a CTA that encourages viewer engagement and builds community.
"""
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert at creating effective call-to-actions that drive viewer engagement and channel growth."},
                {"role": "user", "content": prompt}
            ],
            temperature=self.temperature,
            max_tokens=200
        )
        
        cta = response.choices[0].message.content.strip()
        return clean_text(cta)
    
    async def _generate_subtitle_timings(self, script_content: str) -> List[Dict[str, Any]]:
        """Generate subtitle timings for the script."""
        
        sentences = extract_sentences(script_content)
        subtitle_timings = []
        
        # Estimate timing based on average reading speed
        words_per_minute = 200
        current_time = 0
        
        for sentence in sentences:
            word_count = len(sentence.split())
            duration = (word_count / words_per_minute) * 60
            
            subtitle_timings.append({
                'text': sentence,
                'start_time': current_time,
                'end_time': current_time + duration,
                'duration': duration
            })
            
            current_time += duration
        
        return subtitle_timings
    
    async def optimize_script_for_voice(self, script: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize script for voice synthesis."""
        
        # Combine hook, content, and CTA
        full_script = f"{script['hook']} {script['content']} {script['cta']}"
        
        # Clean and optimize for TTS
        optimized_text = self._optimize_text_for_tts(full_script)
        
        script['optimized_content'] = optimized_text
        return script
    
    def _optimize_text_for_tts(self, text: str) -> str:
        """Optimize text for text-to-speech synthesis."""
        
        # Replace common abbreviations
        replacements = {
            'vs.': 'versus',
            'etc.': 'etcetera',
            'e.g.': 'for example',
            'i.e.': 'that is',
            'Dr.': 'Doctor',
            'Mr.': 'Mister',
            'Mrs.': 'Misses',
            'USD': 'US dollars',
            'EUR': 'Euros',
            'GBP': 'British pounds',
            '%': 'percent',
            '$': 'dollars',
            '€': 'Euros',
            '£': 'pounds'
        }
        
        optimized_text = text
        for old, new in replacements.items():
            optimized_text = optimized_text.replace(old, new)
        
        return clean_text(optimized_text)

