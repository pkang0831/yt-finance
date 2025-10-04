"""
Text processing utilities for content generation and manipulation.
"""

import re
from typing import List, Dict, Any, Optional
from datetime import datetime


def extract_keywords(text: str, max_keywords: int = 5) -> List[str]:
    """Extract keywords from text using simple heuristics."""
    
    # Remove common stop words
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
        'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
        'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those',
        'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her',
        'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our', 'their'
    }
    
    # Clean and split text
    text = re.sub(r'[^\w\s]', ' ', text.lower())
    words = text.split()
    
    # Filter out stop words and short words
    keywords = [
        word for word in words 
        if len(word) > 2 and word not in stop_words
    ]
    
    # Count frequency and return top keywords
    word_freq = {}
    for word in keywords:
        word_freq[word] = word_freq.get(word, 0) + 1
    
    # Sort by frequency and return top keywords
    sorted_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, _ in sorted_keywords[:max_keywords]]


def clean_text(text: str) -> str:
    """Clean text by removing extra whitespace and special characters."""
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove leading/trailing whitespace
    text = text.strip()
    return text


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to maximum length with suffix."""
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def format_duration(seconds: int) -> str:
    """Format duration in seconds to MM:SS format."""
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes:02d}:{seconds:02d}"


def parse_duration(duration_str: str) -> int:
    """Parse duration string (MM:SS) to seconds."""
    try:
        parts = duration_str.split(':')
        if len(parts) == 2:
            minutes, seconds = map(int, parts)
            return minutes * 60 + seconds
        elif len(parts) == 1:
            return int(parts[0])
        else:
            raise ValueError("Invalid duration format")
    except ValueError:
        return 0


def generate_timestamp() -> str:
    """Generate current timestamp string."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def sanitize_filename(filename: str) -> str:
    """Sanitize filename by removing invalid characters."""
    # Remove invalid characters for filenames
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove extra spaces and dots
    filename = re.sub(r'\s+', '_', filename)
    filename = filename.strip('._')
    return filename


def extract_sentences(text: str) -> List[str]:
    """Extract sentences from text."""
    # Simple sentence splitting (can be improved with NLP libraries)
    sentences = re.split(r'[.!?]+', text)
    return [s.strip() for s in sentences if s.strip()]


def count_words(text: str) -> int:
    """Count words in text."""
    words = re.findall(r'\b\w+\b', text)
    return len(words)


def estimate_reading_time(text: str, words_per_minute: int = 200) -> int:
    """Estimate reading time in seconds."""
    word_count = count_words(text)
    minutes = word_count / words_per_minute
    return int(minutes * 60)


def create_hook(text: str, max_length: int = 100) -> str:
    """Create a hook from text by taking the first compelling sentence."""
    sentences = extract_sentences(text)
    
    for sentence in sentences:
        if len(sentence) <= max_length and sentence:
            # Look for compelling words
            compelling_words = ['breaking', 'urgent', 'shocking', 'amazing', 
                              'incredible', 'surprising', 'important', 'critical']
            if any(word in sentence.lower() for word in compelling_words):
                return sentence
    
    # Fallback to first sentence
    if sentences:
        return truncate_text(sentences[0], max_length)
    
    return truncate_text(text, max_length)

