"""
Pydantic schemas for testcase API requests and responses.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID


class TestCaseBase(BaseModel):
    """Base schema for testcase."""
    name: str = Field(..., description="Test case name")
    description: Optional[str] = Field(None, description="Test case description")
    tags: Optional[str] = Field(None, description="Comma-separated tags")


class TestCaseCreate(TestCaseBase):
    """Schema for creating a new testcase."""
    test_file_id: int = Field(..., description="Parent test file ID")


class TestCaseResponse(TestCaseBase):
    """Schema for testcase response."""
    id: int = Field(..., description="Test case ID")
    testcase_uid: UUID = Field(..., description="Test case unique identifier (UUID)")
    test_file_id: int = Field(..., description="Parent test file ID")
    
    class Config:
        from_attributes = True


class TestCaseListResponse(BaseModel):
    """Schema for list of testcases."""
    testcases: List[TestCaseResponse] = Field(..., description="List of testcases")
    total: int = Field(..., description="Total number of testcases")
