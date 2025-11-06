import os
from functools import lru_cache
from typing import Optional


class Settings:
    """Application settings loaded from environment variables."""

    # Ditto configuration
    DITTO_BASE_URL: str
    DITTO_USERNAME: Optional[str]
    DITTO_PASSWORD: Optional[str]
    DITTO_AUTH: Optional[str]

    # Graph API configuration
    GRAPH_API_BASE_URL: Optional[str]
    GRAPH_AUTH_BEARER: Optional[str]

    # HTTP configuration
    HTTP_TIMEOUT_SECONDS: float
    HTTP_RETRIES: int

    # Fallback simulation toggle
    ENABLE_INMEMORY_GRAPH: bool
    ENABLE_INMEMORY_DITTO: bool

    def __init__(self) -> None:
        # Defaults align with typical local dev placeholders used in Robot tests
        self.DITTO_BASE_URL = os.getenv("DITTO_BASE_URL", "http://localhost:8080/api/2")
        # For Ditto auth, either set DITTO_AUTH as "Basic <base64>" or username/password
        self.DITTO_AUTH = os.getenv("DITTO_AUTH")
        self.DITTO_USERNAME = os.getenv("DITTO_USERNAME")
        self.DITTO_PASSWORD = os.getenv("DITTO_PASSWORD")

        self.GRAPH_API_BASE_URL = os.getenv("GRAPH_API_BASE_URL")  # optional
        self.GRAPH_AUTH_BEARER = os.getenv("GRAPH_AUTH")

        self.HTTP_TIMEOUT_SECONDS = float(os.getenv("HTTP_TIMEOUT_SECONDS", "10"))
        self.HTTP_RETRIES = int(os.getenv("HTTP_RETRIES", "2"))

        # In-memory fallbacks for local/simulated runs
        self.ENABLE_INMEMORY_GRAPH = os.getenv("ENABLE_INMEMORY_GRAPH", "true").lower() == "true"
        self.ENABLE_INMEMORY_DITTO = os.getenv("ENABLE_INMEMORY_DITTO", "false").lower() == "true"


# PUBLIC_INTERFACE
@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
