"""
CRUD operations for testcases.
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from ..models.testcase import TestCase
from ..schemas.testcase import TestCaseCreate


# PUBLIC_INTERFACE
def get_testcase(db: Session, testcase_id: int) -> Optional[TestCase]:
    """
    Get a testcase by ID.
    
    Args:
        db: Database session
        testcase_id: Test case ID
        
    Returns:
        Optional[TestCase]: Test case if found, None otherwise
    """
    return db.query(TestCase).filter(TestCase.id == testcase_id).first()


# PUBLIC_INTERFACE
def get_testcases_by_file(db: Session, test_file_id: int) -> List[TestCase]:
    """
    Get all testcases for a specific test file.
    
    Args:
        db: Database session
        test_file_id: Test file ID
        
    Returns:
        List[TestCase]: List of testcases
    """
    return db.query(TestCase).filter(TestCase.test_file_id == test_file_id).all()


# PUBLIC_INTERFACE
def create_testcase(db: Session, testcase: TestCaseCreate) -> TestCase:
    """
    Create a new testcase.
    
    Args:
        db: Database session
        testcase: Test case creation data
        
    Returns:
        TestCase: Created testcase
    """
    db_testcase = TestCase(**testcase.model_dump())
    db.add(db_testcase)
    db.commit()
    db.refresh(db_testcase)
    return db_testcase


# PUBLIC_INTERFACE
def create_testcases_bulk(db: Session, testcases: List[dict], test_file_id: int) -> List[TestCase]:
    """
    Create multiple testcases in bulk.
    
    Args:
        db: Database session
        testcases: List of testcase dictionaries
        test_file_id: Parent test file ID
        
    Returns:
        List[TestCase]: List of created testcases
    """
    db_testcases = []
    for tc_data in testcases:
        db_testcase = TestCase(
            test_file_id=test_file_id,
            name=tc_data['name'],
            description=tc_data.get('description'),
            tags=tc_data.get('tags')
        )
        db.add(db_testcase)
        db_testcases.append(db_testcase)
    
    db.commit()
    for tc in db_testcases:
        db.refresh(tc)
    return db_testcases


# PUBLIC_INTERFACE
def delete_testcase(db: Session, testcase_id: int) -> bool:
    """
    Delete a testcase.
    
    Args:
        db: Database session
        testcase_id: Test case ID
        
    Returns:
        bool: True if deleted, False if not found
    """
    db_testcase = get_testcase(db, testcase_id)
    if not db_testcase:
        return False
    
    db.delete(db_testcase)
    db.commit()
    return True
