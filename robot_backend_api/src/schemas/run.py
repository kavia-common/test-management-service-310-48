"""
Pydantic schemas for test run API requests and responses.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any
from models.run import RunStatus


class RunBase(BaseModel):
    """Base schema for test run."""
    test_file_id: Optional[int] = Field(None, description="Test file ID (for full file runs)")
    testcase_id: Optional[int] = Field(None, description="Test case ID (for specific testcase runs)")
    run_config_id: Optional[int] = Field(None, description="Run configuration ID")
    group_id: Optional[str] = Field(None, description="Optional grouping ID for batch executions")
    group_name: Optional[str] = Field(None, description="Optional grouping display name")


class RunCreate(RunBase):
    """Schema for creating a new test run."""
    variables: Optional[Dict[str, Any]] = Field(None, description="Variables to pass to robot execution")


class RunTestCaseRequest(BaseModel):
    """Schema for running a specific testcase."""
    testcase_id: int = Field(..., description="Test case ID to run")
    run_config_id: Optional[int] = Field(None, description="Run configuration ID")
    variables: Optional[Dict[str, Any]] = Field(None, description="Variables to pass to robot execution")


class RunQueueExecuteRequest(BaseModel):
    """Schema for batch execution request."""
    run_config_id: int = Field(..., description="Run configuration ID to use")
    test_file_ids: Optional[list[int]] = Field(None, description="List of test file IDs to execute")
    testcase_ids: Optional[list[int]] = Field(None, description="List of testcase IDs to execute")


class RunResponse(BaseModel):
    """Schema for test run response."""
    id: int = Field(..., description="Run ID")
    test_file_id: Optional[int] = Field(None, description="Test file ID")
    testcase_id: Optional[int] = Field(None, description="Test case ID")
    run_config_id: Optional[int] = Field(None, description="Run configuration ID")
    group_id: Optional[str] = Field(None, description="Grouping ID")
    group_name: Optional[str] = Field(None, description="Grouping name")
    status: RunStatus = Field(..., description="Run status")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    log_path: Optional[str] = Field(None, description="Log file path in storage")
    output_path: Optional[str] = Field(None, description="Output XML path in storage")
    report_path: Optional[str] = Field(None, description="Report HTML path in storage")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    class Config:
        from_attributes = True


class RunLogsResponse(BaseModel):
    """Schema for run logs response."""
    run_id: int = Field(..., description="Run ID")
    log_content: Optional[str] = Field(None, description="Log file content")
    log_url: Optional[str] = Field(None, description="Presigned URL for log file")
    output_url: Optional[str] = Field(None, description="Presigned URL for output.xml")
    report_url: Optional[str] = Field(None, description="Presigned URL for report.html")
