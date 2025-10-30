"""
CRUD operations for test files.
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from ..models.test_file import TestFile
from ..schemas.test_file import TestFileCreate, TestFileUpdate


# PUBLIC_INTERFACE
def get_test_file(db: Session, test_file_id: int) -> Optional[TestFile]:
    """
    Get a test file by ID.
    
    Args:
        db: Database session
        test_file_id: Test file ID
        
    Returns:
        Optional[TestFile]: Test file if found, None otherwise
    """
    return db.query(TestFile).filter(TestFile.id == test_file_id).first()


# PUBLIC_INTERFACE
def get_test_files(db: Session, skip: int = 0, limit: int = 100) -> List[TestFile]:
    """
    Get a list of test files.
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List[TestFile]: List of test files
    """
    return db.query(TestFile).offset(skip).limit(limit).all()


# PUBLIC_INTERFACE
def create_test_file(db: Session, test_file: TestFileCreate, storage_path: str) -> TestFile:
    """
    Create a new test file record.
    
    Args:
        db: Database session
        test_file: Test file creation data
        storage_path: Path to file in storage
        
    Returns:
        TestFile: Created test file
    """
    db_test_file = TestFile(
        name=test_file.name,
        description=test_file.description,
        storage_path=storage_path
    )
    db.add(db_test_file)
    db.commit()
    db.refresh(db_test_file)
    return db_test_file


# PUBLIC_INTERFACE
def update_test_file(db: Session, test_file_id: int, test_file_update: TestFileUpdate) -> Optional[TestFile]:
    """
    Update a test file.
    
    Args:
        db: Database session
        test_file_id: Test file ID
        test_file_update: Update data
        
    Returns:
        Optional[TestFile]: Updated test file if found, None otherwise
    """
    db_test_file = get_test_file(db, test_file_id)
    if not db_test_file:
        return None
    
    update_data = test_file_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_test_file, key, value)
    
    db.commit()
    db.refresh(db_test_file)
    return db_test_file


# PUBLIC_INTERFACE
def delete_test_file(db: Session, test_file_id: int) -> bool:
    """
    Delete a test file.
    
    Args:
        db: Database session
        test_file_id: Test file ID
        
    Returns:
        bool: True if deleted, False if not found
    """
    db_test_file = get_test_file(db, test_file_id)
    if not db_test_file:
        return False
    
    db.delete(db_test_file)
    db.commit()
    return True
