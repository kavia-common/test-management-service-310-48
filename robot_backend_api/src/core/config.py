"""
Core configuration module for the Robot Framework Test Management API.
Loads settings from environment variables.
"""
from pydantic_settings import BaseSettings
from pathlib import Path

# Get the project root directory (2 levels up from this file)
PROJECT_ROOT = Path(__file__).parent.parent.parent


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Attributes:
        app_name: Application name
        app_version: Application version
        database_url: PostgreSQL connection string
        minio_endpoint: MinIO server endpoint
        minio_access_key: MinIO access key
        minio_secret_key: MinIO secret key
        minio_bucket_name: MinIO bucket for storing robot files and logs
        minio_secure: Whether to use HTTPS for MinIO
        robot_execution_timeout: Default timeout for robot test execution in seconds
    """
    app_name: str = "Robot Framework Test Management API"
    app_version: str = "1.0.0"
    
    # Database settings - REQUIRED environment variable
    database_url: str
    
    # MinIO settings - REQUIRED environment variables
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket_name: str = "robot-tests"
    minio_secure: bool = False
    
    # Robot Framework execution settings
    robot_execution_timeout: int = 300  # 5 minutes default
    
    class Config:
        env_file = str(PROJECT_ROOT / ".env")
        case_sensitive = False
        extra = "ignore"


# Global settings instance
settings = Settings()
