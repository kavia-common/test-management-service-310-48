"""
CRUD operations for input variables.
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from ..models.input_variable import InputVariable


# PUBLIC_INTERFACE
def get_variables_by_test_file(db: Session, test_file_id: int) -> List[InputVariable]:
    """
    Get all variables for a specific test file.
    
    Args:
        db: Database session
        test_file_id: Test file ID
        
    Returns:
        List[InputVariable]: List of variables
    """
    return db.query(InputVariable).filter(
        InputVariable.test_file_id == test_file_id,
        InputVariable.testcase_id.is_(None)
    ).all()


# PUBLIC_INTERFACE
def get_variables_by_testcase(db: Session, test_file_id: int, testcase_id: int) -> List[InputVariable]:
    """
    Get all variables for a specific testcase.
    
    Args:
        db: Database session
        test_file_id: Test file ID
        testcase_id: Test case ID
        
    Returns:
        List[InputVariable]: List of variables
    """
    return db.query(InputVariable).filter(
        InputVariable.test_file_id == test_file_id,
        InputVariable.testcase_id == testcase_id
    ).all()


# PUBLIC_INTERFACE
def create_variables_bulk(db: Session, variables: List[dict], test_file_id: int, testcase_id: Optional[int] = None) -> List[InputVariable]:
    """
    Create multiple variables in bulk.
    
    Args:
        db: Database session
        variables: List of variable dictionaries
        test_file_id: Parent test file ID
        testcase_id: Optional testcase ID for testcase-level variables
        
    Returns:
        List[InputVariable]: List of created variables
    """
    db_variables = []
    for var_data in variables:
        db_var = InputVariable(
            test_file_id=test_file_id,
            testcase_id=testcase_id,
            name=var_data['name'],
            default_value=var_data.get('default_value'),
            description=var_data.get('description')
        )
        db.add(db_var)
        db_variables.append(db_var)
    
    db.commit()
    for var in db_variables:
        db.refresh(var)
    return db_variables


# PUBLIC_INTERFACE
def delete_variables_by_test_file(db: Session, test_file_id: int) -> bool:
    """
    Delete all variables for a test file.
    
    Args:
        db: Database session
        test_file_id: Test file ID
        
    Returns:
        bool: True if deleted
    """
    db.query(InputVariable).filter(InputVariable.test_file_id == test_file_id).delete()
    db.commit()
    return True
