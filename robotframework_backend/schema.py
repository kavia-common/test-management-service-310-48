"""Python schema module for Robot Framework management API."""

from typing import List, Optional, Dict
from pydantic import BaseModel


class TestCreateResponse(BaseModel):
    """Response schema for a created test."""
    id: str
    name: str
    description: Optional[str]


class TestMetadata(BaseModel):
    """Metadata schema for tests."""
    id: str
    name: str
    description: Optional[str]
    filename: str
    created_at: str


class RunCreateRequest(BaseModel):
    """Schema for creating a test run request."""
    cases: Optional[List[str]] = None
    variables: Optional[Dict[str, str]] = None
    run_name: Optional[str] = None
    tags: Optional[List[str]] = None


class RunSummary(BaseModel):
    """Schema for summarizing a test run."""
    id: str
    test_id: str
    run_name: Optional[str]
    status: str
    started_at: Optional[str]
    finished_at: Optional[str]
    summary: Optional[dict]
