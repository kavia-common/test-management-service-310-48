"""
CRUD operations for input variables.
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from models.input_variable import InputVariable
import logging

logger = logging.getLogger(__name__)


# PUBLIC_INTERFACE
def get_variables_by_test_file(db: Session, test_file_id: int) -> List[InputVariable]:
    """
    Get all file-level variables for a specific test file (testcase_id is NULL).
    
    Args:
        db: Database session
        test_file_id: Test file ID
        
    Returns:
        List[InputVariable]: List of variables
    """
    logger.info(f"Querying file-level variables for test_file_id={test_file_id}")
    variables = db.query(InputVariable).filter(
        InputVariable.test_file_id == test_file_id,
        InputVariable.testcase_id.is_(None)
    ).all()
    logger.info(f"Found {len(variables)} file-level variables for test_file_id={test_file_id}")
    return variables


# PUBLIC_INTERFACE
def get_variables_by_testcase(db: Session, test_file_id: int, testcase_id: int) -> List[InputVariable]:
    """
    Get all testcase-level variables for a specific testcase.
    
    Args:
        db: Database session
        test_file_id: Test file ID
        testcase_id: Test case ID
        
    Returns:
        List[InputVariable]: List of variables
    """
    logger.info(f"Querying testcase-level variables for test_file_id={test_file_id}, testcase_id={testcase_id}")
    variables = db.query(InputVariable).filter(
        InputVariable.test_file_id == test_file_id,
        InputVariable.testcase_id == testcase_id
    ).all()
    logger.info(f"Found {len(variables)} testcase-level variables")
    
    if not variables:
        # Debug: check if variables exist with just testcase_id
        alt_vars = db.query(InputVariable).filter(InputVariable.testcase_id == testcase_id).all()
        logger.warning(
            f"No variables found for test_file_id={test_file_id}, testcase_id={testcase_id}, "
            f"but found {len(alt_vars)} variables with just testcase_id={testcase_id}"
        )
        if alt_vars:
            for v in alt_vars:
                logger.debug(f"  Variable '{v.name}' has test_file_id={v.test_file_id}, testcase_id={v.testcase_id}")
    
    return variables


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
    var_type = "testcase-level" if testcase_id else "file-level"
    logger.info(f"Creating {len(variables)} {var_type} variables for test_file_id={test_file_id}, testcase_id={testcase_id}")
    
    db_variables = []
    for var_data in variables:
        var_name = var_data.get('name', 'UNKNOWN')
        logger.debug(f"  Creating variable: {var_name} (testcase_id={testcase_id})")
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
    
    logger.info(f"Successfully created {len(db_variables)} {var_type} variables")
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
    logger.info(f"Deleting all variables for test_file_id={test_file_id}")
    count = db.query(InputVariable).filter(InputVariable.test_file_id == test_file_id).delete()
    db.commit()
    logger.info(f"Deleted {count} variables for test_file_id={test_file_id}")
    return True
