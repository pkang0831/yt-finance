"""
I/O utilities for file operations and configuration management.
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional


def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from YAML file."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML configuration: {e}")


def save_config(config: Dict[str, Any], config_path: str) -> None:
    """Save configuration to YAML file."""
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, indent=2)


def load_json(file_path: str) -> Dict[str, Any]:
    """Load JSON data from file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON file {file_path}: {e}")


def save_json(data: Dict[str, Any], file_path: str) -> None:
    """Save data to JSON file."""
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_jsonl(file_path: str) -> List[Dict[str, Any]]:
    """Load JSONL data from file."""
    data = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    data.append(json.loads(line))
    except FileNotFoundError:
        pass
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSONL file {file_path}: {e}")
    
    return data


def save_jsonl(data: List[Dict[str, Any]], file_path: str) -> None:
    """Save data to JSONL file."""
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')


def ensure_directories(config: Dict[str, Any]) -> None:
    """Ensure all required directories exist."""
    paths = config.get("paths", {})
    
    directories = [
        paths.get("workitems", "./data/workitems"),
        paths.get("outputs", "./data/outputs"),
        paths.get("logs", "./data/logs"),
        paths.get("oauth", "./yt_oauth")
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)


def get_output_path(config: Dict[str, Any], filename: str) -> str:
    """Get full output path for a file."""
    output_dir = config.get("paths", {}).get("outputs", "./data/outputs")
    return str(Path(output_dir) / filename)


def get_workitem_path(config: Dict[str, Any], filename: str) -> str:
    """Get full workitem path for a file."""
    workitems_dir = config.get("paths", {}).get("workitems", "./data/workitems")
    return str(Path(workitems_dir) / filename)


def cleanup_old_files(directory: str, days: int = 7) -> None:
    """Clean up files older than specified days."""
    import time
    from datetime import datetime, timedelta
    
    cutoff_time = time.time() - (days * 24 * 60 * 60)
    directory_path = Path(directory)
    
    if not directory_path.exists():
        return
    
    for file_path in directory_path.iterdir():
        if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
            file_path.unlink()

