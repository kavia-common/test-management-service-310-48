"""
Pydantic schemas for run configuration API requests and responses.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any


class RunConfigBase(BaseModel):
    """Base schema for run configuration."""
    name: str = Field(..., description="Configuration name")
    description: Optional[str] = Field(None, description="Configuration description")
    variables: Optional[Dict[str, Any]] = Field(None, description="Robot variables")
    include_tags: Optional[str] = Field(None, description="Comma-separated tags to include")
    exclude_tags: Optional[str] = Field(None, description="Comma-separated tags to exclude")
    timeout: Optional[int] = Field(None, description="Execution timeout in seconds")


class RunConfigCreate(RunConfigBase):
    """Schema for creating a new run configuration."""
    pass


class RunConfigUpdate(BaseModel):
    """Schema for updating a run configuration."""
    name: Optional[str] = Field(None, description="Configuration name")
    description: Optional[str] = Field(None, description="Configuration description")
    variables: Optional[Dict[str, Any]] = Field(None, description="Robot variables")
    include_tags: Optional[str] = Field(None, description="Comma-separated tags to include")
    exclude_tags: Optional[str] = Field(None, description="Comma-separated tags to exclude")
    timeout: Optional[int] = Field(None, description="Execution timeout in seconds")


class RunConfigResponse(RunConfigBase):
    """Schema for run configuration response."""
    id: int = Field(..., description="Configuration ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True
