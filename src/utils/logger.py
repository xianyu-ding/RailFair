"""Logging configuration for the rail delay predictor."""

import sys
from pathlib import Path
from loguru import logger
from .config import LOGS_DIR, Config

# Remove default handler
logger.remove()

# Add console handler with color
logger.add(
    sys.stdout,
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=Config.LOG_LEVEL
)

# Add file handler
log_file = LOGS_DIR / "rail_predictor_{time:YYYY-MM-DD}.log"
logger.add(
    str(log_file),
    rotation="00:00",  # Rotate at midnight
    retention="30 days",  # Keep logs for 30 days
    compression="zip",  # Compress old logs
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG"  # Log everything to file
)

# Add error file handler
error_log_file = LOGS_DIR / "errors_{time:YYYY-MM-DD}.log"
logger.add(
    str(error_log_file),
    rotation="00:00",
    retention="90 days",
    compression="zip",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="ERROR"  # Only errors and above
)

def get_logger(name: str):
    """Get a logger instance with the given name."""
    return logger.bind(name=name)

__all__ = ["logger", "get_logger"]
