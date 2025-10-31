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
@router.get("/{test_file_id}/{testcase_id}", 
            response_model=dict,
            status_code=status.HTTP_410_GONE,
            deprecated=True,
            summary="[DEPRECATED] Get variables for a testcase",
            description="This endpoint is deprecated. Use GET /tests/{test_uid}/testcases/{testcase_uid}/required-variables instead.")
async def get_testcase_variables_deprecated(
    test_file_id: int,
    testcase_id: int,
    db: Session = Depends(get_db)
) -> dict:
    """
    DEPRECATED: Get testcase-level variables.
    
    This endpoint has been deprecated and will be removed in a future version.
    Please use the new endpoint: GET /tests/{test_identifier}/testcases/{case_identifier}/required-variables
    
    The new endpoint supports:
    - UUID-based identifiers for stable referencing
    - Both test_uid/testcase_uid and legacy integer IDs
    - Case name resolution
    - Enhanced variable analysis
    
    Args:
        test_file_id: Test file ID (deprecated)
        testcase_id: Test case ID (deprecated)
        db: Database session
        
    Returns:
        dict: Deprecation notice with migration instructions
    """
    logger.warning(f"DEPRECATED endpoint called: /inputs/{test_file_id}/{testcase_id}")
    
    # Try to provide helpful migration info
    db_testcase = crud_testcase.get_testcase(db, testcase_id)
    db_test_file = crud_test_file.get_test_file(db, test_file_id)
    
    migration_info = {
        "status": "deprecated",
        "message": "This endpoint has been deprecated. Please migrate to the new endpoint.",
        "new_endpoint": "/tests/{test_identifier}/testcases/{case_identifier}/required-variables",
        "documentation": "See /docs for complete API documentation",
        "migration_guide": {
            "description": "The new endpoint provides enhanced functionality with UUID support",
            "examples": [
                "GET /tests/123/testcases/456/required-variables (using integer IDs)",
                "GET /tests/{test_uid}/testcases/{testcase_uid}/required-variables (using UUIDs)",
                "GET /tests/123/testcases/My%20Test%20Case/required-variables (using case name)"
            ]
        }
    }
    
    if db_test_file and db_testcase:
        migration_info["suggested_new_url"] = f"/tests/{db_test_file.test_uid}/testcases/{db_testcase.testcase_uid}/required-variables"
        migration_info["alternative_url"] = f"/tests/{test_file_id}/testcases/{testcase_id}/required-variables"
    
    return migration_info
