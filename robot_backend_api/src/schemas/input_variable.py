"""
Pydantic schemas for input variable API requests and responses.
"""
from pydantic import BaseModel, Field
from typing import Optional


class InputVariableBase(BaseModel):
    """Base schema for input variable."""
    name: str = Field(..., description="Variable name")
    default_value: Optional[str] = Field(None, description="Default value")
    description: Optional[str] = Field(None, description="Variable description")


class InputVariableResponse(InputVariableBase):
    """Schema for input variable response."""
    id: int = Field(..., description="Variable ID")
    test_file_id: int = Field(..., description="Test file ID")
    testcase_id: Optional[int] = Field(None, description="Test case ID (if testcase-level)")
    
    class Config:
        from_attributes = True
