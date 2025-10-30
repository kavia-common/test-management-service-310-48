"""
API routes for testcase management.
Provides endpoints for retrieving testcases from robot test files.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from schemas.testcase import TestCaseListResponse
from crud import testcase as crud_testcase
from crud import test_file as crud_test_file

router = APIRouter(prefix="/tests", tags=["Test Cases"])


# PUBLIC_INTERFACE
@router.get("/{test_file_id}/testcases", response_model=TestCaseListResponse,
            summary="Get testcases for a test file",
            description="Retrieve all testcases extracted from a specific robot test file.")
async def get_testcases(
    test_file_id: int,
    db: Session = Depends(get_db)
) -> TestCaseListResponse:
    """
    Get all testcases for a test file.
    
    Args:
        test_file_id: Test file ID
        db: Database session
        
    Returns:
        TestCaseListResponse: List of testcases with total count
        
    Raises:
        HTTPException: If test file not found
    """
    # Verify test file exists
    db_test_file = crud_test_file.get_test_file(db, test_file_id)
    if not db_test_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test file not found"
        )
    
    # Get testcases
    testcases = crud_testcase.get_testcases_by_file(db, test_file_id)
    
    return TestCaseListResponse(
        testcases=testcases,
        total=len(testcases)
    )
