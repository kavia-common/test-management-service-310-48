"""
Pydantic schemas for test file API requests and responses.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from uuid import UUID


class TestFileBase(BaseModel):
    """Base schema for test file."""
    name: str = Field(..., description="Test file name")
    description: Optional[str] = Field(None, description="Test file description")


class TestFileCreate(TestFileBase):
    """Schema for creating a new test file."""
    pass


class TestFileUpdate(BaseModel):
    """Schema for updating a test file."""
    name: Optional[str] = Field(None, description="Test file name")
    description: Optional[str] = Field(None, description="Test file description")


class TestFileResponse(TestFileBase):
    """Schema for test file response."""
    id: int = Field(..., description="Test file ID")
    test_uid: UUID = Field(..., description="Test file unique identifier (UUID)")
    storage_path: str = Field(..., description="Storage path in MinIO")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True


class TestFileDetailResponse(TestFileResponse):
    """Schema for detailed test file response with testcases."""
    testcase_count: int = Field(..., description="Number of testcases in this file")
    
    class Config:
        from_attributes = True
