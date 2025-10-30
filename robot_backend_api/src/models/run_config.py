"""
Database model for test run configurations.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from ..core.database import Base


class RunConfig(Base):
    """
    Represents a reusable test run configuration.
    
    Attributes:
        id: Primary key
        name: Configuration name
        description: Configuration description
        variables: JSON object of robot variables
        include_tags: Comma-separated tags to include
        exclude_tags: Comma-separated tags to exclude
        timeout: Execution timeout in seconds
        created_at: Creation timestamp
        updated_at: Last update timestamp
        runs: Related test runs using this configuration
    """
    __tablename__ = "run_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True, unique=True)
    description = Column(Text, nullable=True)
    variables = Column(JSON, nullable=True)
    include_tags = Column(Text, nullable=True)
    exclude_tags = Column(Text, nullable=True)
    timeout = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    runs = relationship("Run", back_populates="run_config")
