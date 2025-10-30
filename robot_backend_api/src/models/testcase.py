"""
Database model for individual test cases within robot test files.
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from ..core.database import Base


class TestCase(Base):
    """
    Represents an individual test case extracted from a robot test file.
    
    Attributes:
        id: Primary key
        test_file_id: Foreign key to parent test file
        name: Test case name
        description: Test case description/documentation
        tags: Comma-separated tags
        test_file: Parent test file relationship
        runs: Related test runs
    """
    __tablename__ = "testcases"
    
    id = Column(Integer, primary_key=True, index=True)
    test_file_id = Column(Integer, ForeignKey("test_files.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)
    
    # Relationships
    test_file = relationship("TestFile", back_populates="testcases")
    runs = relationship("Run", back_populates="testcase")
    input_variables = relationship("InputVariable", back_populates="testcase", cascade="all, delete-orphan")
