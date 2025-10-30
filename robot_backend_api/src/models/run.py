"""
Database model for test execution runs.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum
from core.database import Base


class RunStatus(str, Enum):
    """Enumeration of possible run statuses."""
    QUEUED = "queued"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"


class Run(Base):
    """
    Represents a test execution run.
    
    Attributes:
        id: Primary key
        test_file_id: Foreign key to test file (optional for testcase runs)
        testcase_id: Foreign key to specific testcase (optional for full file runs)
        run_config_id: Foreign key to run configuration (optional)
        status: Current execution status
        started_at: Execution start timestamp
        completed_at: Execution completion timestamp
        log_path: Path to execution log in storage
        output_path: Path to output.xml in storage
        report_path: Path to report.html in storage
        error_message: Error message if failed
        test_file: Parent test file relationship
        testcase: Specific testcase relationship
        run_config: Run configuration relationship
    """
    __tablename__ = "runs"
    
    id = Column(Integer, primary_key=True, index=True)
    test_file_id = Column(Integer, ForeignKey("test_files.id", ondelete="CASCADE"), nullable=True, index=True)
    testcase_id = Column(Integer, ForeignKey("testcases.id", ondelete="CASCADE"), nullable=True, index=True)
    run_config_id = Column(Integer, ForeignKey("run_configs.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(SQLEnum(RunStatus), default=RunStatus.QUEUED, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    log_path = Column(String(500), nullable=True)
    output_path = Column(String(500), nullable=True)
    report_path = Column(String(500), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    test_file = relationship("TestFile", back_populates="runs")
    testcase = relationship("TestCase", back_populates="runs")
    run_config = relationship("RunConfig", back_populates="runs")
