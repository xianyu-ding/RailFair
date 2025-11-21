"""Configuration management for the rail delay predictor."""

import os
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
CACHE_DIR = DATA_DIR / "cache"
MODELS_DIR = PROJECT_ROOT / "models"
LOGS_DIR = PROJECT_ROOT / "logs"

# Ensure directories exist
for directory in [RAW_DATA_DIR, PROCESSED_DATA_DIR, CACHE_DIR, MODELS_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)


class Config:
    """Central configuration class."""
    
    # HSP API Configuration
    HSP_SERVICE_DETAILS_URL = os.getenv(
        "HSP_SERVICE_DETAILS_URL",
        "https://hsp-prod.rockshore.net/api/v1/serviceDetails"
    )
    HSP_SERVICE_METRICS_URL = os.getenv(
        "HSP_SERVICE_METRICS_URL",
        "https://hsp-prod.rockshore.net/api/v1/serviceMetrics"
    )
    HSP_USERNAME = os.getenv("HSP_USERNAME", "")
    HSP_PASSWORD = os.getenv("HSP_PASSWORD", "")
    
    # Darwin Push Port Configuration
    DARWIN_USERNAME = os.getenv("DARWIN_USERNAME", "")
    DARWIN_PASSWORD = os.getenv("DARWIN_PASSWORD", "")
    DARWIN_MESSAGING_HOST = os.getenv(
        "DARWIN_MESSAGING_HOST",
        "darwin-dist-44ae45.nationalrail.co.uk"
    )
    DARWIN_STOMP_PORT = int(os.getenv("DARWIN_STOMP_PORT", "61613"))
    DARWIN_OPENWIRE_PORT = int(os.getenv("DARWIN_OPENWIRE_PORT", "61616"))
    DARWIN_LIVE_FEED_TOPIC = os.getenv(
        "DARWIN_LIVE_FEED_TOPIC",
        "/topic/darwin.pushport-v16"
    )
    DARWIN_STATUS_TOPIC = os.getenv(
        "DARWIN_STATUS_TOPIC",
        "/topic/darwin.status"
    )
    
    # Darwin S3 Configuration
    DARWIN_S3_BUCKET = os.getenv("DARWIN_S3_BUCKET", "")
    DARWIN_S3_PREFIX = os.getenv("DARWIN_S3_PREFIX", "")
    DARWIN_AWS_ACCESS_KEY = os.getenv("DARWIN_AWS_ACCESS_KEY", "")
    DARWIN_AWS_SECRET_KEY = os.getenv("DARWIN_AWS_SECRET_KEY", "")
    DARWIN_AWS_REGION = os.getenv("DARWIN_AWS_REGION", "eu-west-1")
    
    # Knowledgebase API Configuration
    KB_API_BASE_URL = os.getenv("KB_API_BASE_URL", "https://api.rsp.nationalrail.co.uk")
    KB_USERNAME = os.getenv("KB_USERNAME", "")
    KB_PASSWORD = os.getenv("KB_PASSWORD", "")
    
    # Database Configuration
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "5432"))
    DB_NAME = os.getenv("DB_NAME", "rail_delay_db")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    
    # Application Settings
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    DATA_RETENTION_DAYS = int(os.getenv("DATA_RETENTION_DAYS", "90"))
    CACHE_EXPIRY_HOURS = int(os.getenv("CACHE_EXPIRY_HOURS", "24"))
    
    @classmethod
    def validate(cls) -> Dict[str, bool]:
        """Validate that required credentials are set."""
        validations = {
            "HSP_API": bool(cls.HSP_USERNAME and cls.HSP_PASSWORD),
            "Darwin": bool(cls.DARWIN_USERNAME and cls.DARWIN_PASSWORD),
            "Knowledgebase": bool(cls.KB_USERNAME and cls.KB_PASSWORD),
            "Database": bool(cls.DB_PASSWORD),
        }
        return validations
    
    @classmethod
    def get_summary(cls) -> Dict[str, Any]:
        """Get configuration summary (without sensitive data)."""
        return {
            "project_root": str(PROJECT_ROOT),
            "data_dir": str(DATA_DIR),
            "hsp_api_url": cls.HSP_SERVICE_DETAILS_URL,
            "darwin_host": cls.DARWIN_MESSAGING_HOST,
            "kb_api_url": cls.KB_API_BASE_URL,
            "log_level": cls.LOG_LEVEL,
            "credentials_status": cls.validate()
        }


# Export commonly used paths
__all__ = [
    "Config",
    "PROJECT_ROOT",
    "DATA_DIR",
    "RAW_DATA_DIR",
    "PROCESSED_DATA_DIR",
    "CACHE_DIR",
    "MODELS_DIR",
    "LOGS_DIR"
]
