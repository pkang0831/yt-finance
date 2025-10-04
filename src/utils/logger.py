"""
Logging utilities for the YouTube AI Finance pipeline.
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Dict, Any


def setup_logger(name: str, config: Dict[str, Any]) -> logging.Logger:
    """Set up a logger with file and console handlers."""
    
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, config.get("logging", {}).get("level", "INFO")))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        config.get("logging", {}).get("format", 
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    log_dir = Path(config.get("paths", {}).get("logs", "./data/logs"))
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / f"{name}.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=config.get("logging", {}).get("max_file_size_mb", 10) * 1024 * 1024,
        backupCount=config.get("logging", {}).get("backup_count", 5)
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)

