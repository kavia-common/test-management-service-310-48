"""
Database model for Robot Framework test files.
"""
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from core.database import Base


class TestFile(Base):
    """
    Represents a Robot Framework test file.
    
    Attributes:
        id: Primary key
        test_uid: Unique identifier (UUID) for stable referencing
        name: Original filename
        description: Optional description
        storage_path: Path to file in MinIO storage
        created_at: Creation timestamp
        updated_at: Last update timestamp
        testcases: Related testcases
        runs: Related test runs
    """
    __tablename__ = "test_files"
    
    id = Column(Integer, primary_key=True, index=True)
    test_uid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    storage_path = Column(String(500), nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    testcases = relationship("TestCase", back_populates="test_file", cascade="all, delete-orphan")
    runs = relationship("Run", back_populates="test_file", cascade="all, delete-orphan")
    input_variables = relationship("InputVariable", back_populates="test_file", cascade="all, delete-orphan")
