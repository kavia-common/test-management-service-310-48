"""
API routes for input variable management.
Provides endpoints for retrieving variables extracted from robot test files.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging

from core.database import get_db
from schemas.input_variable import InputVariableResponse
from crud import input_variable as crud_input_variable
from crud import test_file as crud_test_file
from crud import testcase as crud_testcase

router = APIRouter(prefix="/inputs", tags=["Input Variables"])
logger = logging.getLogger(__name__)


# PUBLIC_INTERFACE
@router.get("/{test_file_id}", response_model=List[InputVariableResponse],
            summary="Get variables for a test file",
            description="Retrieve all file-level variables from a robot test file. Variables with testcase_id are excluded here.")
async def get_test_file_variables(
    test_file_id: int,
    db: Session = Depends(get_db)
) -> List[InputVariableResponse]:
    """
    Get all file-level variables for a test file.
    
    Args:
        test_file_id: Test file ID
        db: Database session
        
    Returns:
        List[InputVariableResponse]: List of variables
        
    Raises:
        HTTPException: If test file not found
    """
    logger.info(f"GET /inputs/{test_file_id} - Fetching file-level variables")
    
    # Verify test file exists
    db_test_file = crud_test_file.get_test_file(db, test_file_id)
    if not db_test_file:
        logger.warning(f"Test file {test_file_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test file not found"
        )
    
    logger.debug(f"Test file found: {db_test_file.name}")
    variables = crud_input_variable.get_variables_by_test_file(db, test_file_id)
    logger.info(f"Returning {len(variables)} file-level variables for test_file_id={test_file_id}")
    return variables


# PUBLIC_INTERFACE
@router.get("/{test_file_id}/{testcase_id}", response_model=List[InputVariableResponse],
            summary="Get variables for a testcase",
            description="Retrieve all testcase-level variables from a specific testcase.")
async def get_testcase_variables(
    test_file_id: int,
    testcase_id: int,
    db: Session = Depends(get_db)
) -> List[InputVariableResponse]:
    """
    Get all testcase-level variables for a testcase.
    
    Args:
        test_file_id: Test file ID
        testcase_id: Test case ID
        db: Database session
        
    Returns:
        List[InputVariableResponse]: List of variables
        
    Raises:
        HTTPException: If test file or testcase not found
    """
    logger.info(f"GET /inputs/{test_file_id}/{testcase_id} - Fetching testcase-level variables")
    
    # Verify test file exists
    db_test_file = crud_test_file.get_test_file(db, test_file_id)
    if not db_test_file:
        logger.warning(f"Test file {test_file_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test file not found"
        )
    
    logger.debug(f"Test file found: {db_test_file.name}")
    
    # Verify testcase exists
    db_testcase = crud_testcase.get_testcase(db, testcase_id)
    if not db_testcase:
        logger.warning(f"Testcase {testcase_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test case not found"
        )
    
    if db_testcase.test_file_id != test_file_id:
        logger.warning(
            f"Testcase {testcase_id} belongs to test_file_id={db_testcase.test_file_id}, "
            f"not test_file_id={test_file_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test case not found or does not belong to specified test file"
        )
    
    logger.debug(f"Testcase found: {db_testcase.name} (belongs to test_file_id={db_testcase.test_file_id})")
    
    variables = crud_input_variable.get_variables_by_testcase(db, test_file_id, testcase_id)
    logger.info(f"Returning {len(variables)} testcase-level variables for test_file_id={test_file_id}, testcase_id={testcase_id}")
    
    return variables
