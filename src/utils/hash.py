"""
Hash utilities for content identification and duplicate detection.
"""

import hashlib
import json
from typing import Dict, Any, Optional
from pathlib import Path


def generate_content_hash(content: str) -> str:
    """Generate SHA-256 hash for content."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def generate_file_hash(file_path: str) -> str:
    """Generate SHA-256 hash for file content."""
    hash_sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    except FileNotFoundError:
        return ""


def generate_workitem_hash(workitem: Dict[str, Any]) -> str:
    """Generate hash for work item based on key fields."""
    # Create a stable representation of the work item
    key_fields = {
        'title': workitem.get('title', ''),
        'summary': workitem.get('summary', ''),
        'source': workitem.get('source', ''),
        'timestamp': workitem.get('timestamp', '')
    }
    
    # Convert to JSON string for consistent hashing
    content = json.dumps(key_fields, sort_keys=True, ensure_ascii=False)
    return generate_content_hash(content)


def generate_script_hash(script: Dict[str, Any]) -> str:
    """Generate hash for script content."""
    key_fields = {
        'content': script.get('content', ''),
        'hook': script.get('hook', ''),
        'cta': script.get('cta', ''),
        'keywords': script.get('keywords', [])
    }
    
    content = json.dumps(key_fields, sort_keys=True, ensure_ascii=False)
    return generate_content_hash(content)


def check_duplicate_content(
    content_hash: str, 
    hash_file_path: str
) -> bool:
    """Check if content hash already exists in hash file."""
    if not Path(hash_file_path).exists():
        return False
    
    try:
        with open(hash_file_path, 'r', encoding='utf-8') as f:
            existing_hashes = set(line.strip() for line in f if line.strip())
        return content_hash in existing_hashes
    except (FileNotFoundError, IOError):
        return False


def save_content_hash(
    content_hash: str, 
    hash_file_path: str,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """Save content hash to hash file with optional metadata."""
    Path(hash_file_path).parent.mkdir(parents=True, exist_ok=True)
    
    hash_entry = content_hash
    if metadata:
        metadata_str = json.dumps(metadata, ensure_ascii=False)
        hash_entry = f"{content_hash}|{metadata_str}"
    
    with open(hash_file_path, 'a', encoding='utf-8') as f:
        f.write(hash_entry + '\n')


def load_content_hashes(hash_file_path: str) -> Dict[str, Dict[str, Any]]:
    """Load content hashes and metadata from hash file."""
    hashes = {}
    
    if not Path(hash_file_path).exists():
        return hashes
    
    try:
        with open(hash_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                if '|' in line:
                    # Hash with metadata
                    hash_part, metadata_str = line.split('|', 1)
                    try:
                        metadata = json.loads(metadata_str)
                        hashes[hash_part] = metadata
                    except json.JSONDecodeError:
                        hashes[hash_part] = {}
                else:
                    # Hash only
                    hashes[line] = {}
    except (FileNotFoundError, IOError):
        pass
    
    return hashes


def cleanup_old_hashes(hash_file_path: str, max_age_days: int = 30) -> None:
    """Clean up old hash entries based on metadata timestamp."""
    import time
    from datetime import datetime, timedelta
    
    cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)
    hashes = load_content_hashes(hash_file_path)
    
    # Filter out old entries
    recent_hashes = {}
    for hash_value, metadata in hashes.items():
        timestamp = metadata.get('timestamp', 0)
        if timestamp > cutoff_time:
            recent_hashes[hash_value] = metadata
    
    # Rewrite file with recent entries only
    if recent_hashes != hashes:
        Path(hash_file_path).unlink(missing_ok=True)
        for hash_value, metadata in recent_hashes.items():
            save_content_hash(hash_value, hash_file_path, metadata)


def generate_unique_filename(base_name: str, extension: str) -> str:
    """Generate unique filename using hash of base name."""
    hash_suffix = generate_content_hash(base_name)[:8]
    return f"{base_name}_{hash_suffix}.{extension}"


def verify_file_integrity(file_path: str, expected_hash: str) -> bool:
    """Verify file integrity by comparing with expected hash."""
    actual_hash = generate_file_hash(file_path)
    return actual_hash == expected_hash

