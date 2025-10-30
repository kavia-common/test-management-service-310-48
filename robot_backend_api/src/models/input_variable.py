"""
Database model for input variables extracted from robot test files.
"""
from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship
from core.database import Base


class InputVariable(Base):
    """
    Represents an input variable defined in a robot test file.
    
    Attributes:
        id: Primary key
        test_file_id: Foreign key to test file
        testcase_id: Foreign key to testcase (optional, for testcase-level variables)
        name: Variable name
        default_value: Default value
        description: Variable description
        test_file: Parent test file relationship
        testcase: Parent testcase relationship (if testcase-level)
    """
    __tablename__ = "input_variables"
    
    id = Column(Integer, primary_key=True, index=True)
    test_file_id = Column(Integer, ForeignKey("test_files.id", ondelete="CASCADE"), nullable=False, index=True)
    testcase_id = Column(Integer, ForeignKey("testcases.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    default_value = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    
    # Relationships
    test_file = relationship("TestFile", back_populates="input_variables")
    testcase = relationship("TestCase", back_populates="input_variables")
