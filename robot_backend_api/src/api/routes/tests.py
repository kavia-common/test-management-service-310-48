"""
API routes for test file management.
Provides endpoints for uploading, managing, and retrieving robot test files.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from typing import List
import tempfile
import os

from core.database import get_db
from schemas.test_file import TestFileResponse, TestFileDetailResponse, TestFileUpdate
from crud import test_file as crud_test_file
from crud import testcase as crud_testcase
from crud import input_variable as crud_input_variable
from services.robot_parser import robot_parser
from services.storage_service import save_robot_file
from core.storage import storage_service

router = APIRouter(prefix="/tests", tags=["Test Files"])


# PUBLIC_INTERFACE
@router.post("/", response_model=TestFileDetailResponse, status_code=status.HTTP_201_CREATED,
             summary="Upload a new robot test file",
             description="Upload a .robot test file, parse it to extract testcases and variables, and store metadata in the database.")
async def upload_test_file(
    file: UploadFile = File(..., description="Robot test file (.robot)"),
    db: Session = Depends(get_db)
) -> TestFileDetailResponse:
    """
    Upload a new robot test file.
    
    Accepts a .robot file, validates it, parses testcases and variables,
    stores the file in MinIO, and creates database records.
    
    Args:
        file: Uploaded robot test file
        db: Database session
        
    Returns:
        TestFileDetailResponse: Created test file with testcase count
        
    Raises:
        HTTPException: If file is invalid or parsing fails
    """
    # Validate file extension
    if not file.filename.endswith('.robot'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must have .robot extension"
        )
    
    # Read file content
    file_content = await file.read()
    
    # Save to temporary location for parsing
    with tempfile.NamedTemporaryFile(delete=False, suffix='.robot') as tmp_file:
        tmp_file.write(file_content)
        tmp_file_path = tmp_file.name
    
    try:
        # Validate robot file
        if not robot_parser.validate_robot_file(tmp_file_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid robot test file"
            )
        
        # Parse testcases and variables
        testcases, variables = robot_parser.parse_file(tmp_file_path)
        
        # Create test file record first (without storage_path)
        from schemas.test_file import TestFileCreate
        test_file_create = TestFileCreate(name=file.filename, description=None)
        db_test_file = crud_test_file.create_test_file(
            db,
            test_file_create,
            f"pending_{file.filename}"  # Temporary storage path
        )
        
        # Upload to storage with actual ID
        storage_path = save_robot_file(file_content, db_test_file.id, file.filename)
        
        # Update storage path
        db_test_file.storage_path = storage_path
        db.commit()
        db.refresh(db_test_file)
        
        # Create testcases
        crud_testcase.create_testcases_bulk(db, testcases, db_test_file.id)
        
        # Create variables
        crud_input_variable.create_variables_bulk(db, variables, db_test_file.id)
        
        # Return response
        response = TestFileDetailResponse(
            id=db_test_file.id,
            name=db_test_file.name,
            description=db_test_file.description,
            storage_path=db_test_file.storage_path,
            created_at=db_test_file.created_at,
            updated_at=db_test_file.updated_at,
            testcase_count=len(testcases)
        )
        return response
        
    finally:
        # Cleanup temp file
        if os.path.exists(tmp_file_path):
            os.unlink(tmp_file_path)


# PUBLIC_INTERFACE
@router.get("/", response_model=List[TestFileResponse],
            summary="List all test files",
            description="Retrieve a paginated list of all robot test files.")
async def list_test_files(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
) -> List[TestFileResponse]:
    """
    List all test files.
    
    Args:
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        db: Database session
        
    Returns:
        List[TestFileResponse]: List of test files
    """
    test_files = crud_test_file.get_test_files(db, skip=skip, limit=limit)
    return test_files


# PUBLIC_INTERFACE
@router.get("/{test_file_id}", response_model=TestFileDetailResponse,
            summary="Get test file details",
            description="Retrieve detailed information about a specific test file including testcase count.")
async def get_test_file(
    test_file_id: int,
    db: Session = Depends(get_db)
) -> TestFileDetailResponse:
    """
    Get test file by ID.
    
    Args:
        test_file_id: Test file ID
        db: Database session
        
    Returns:
        TestFileDetailResponse: Test file details
        
    Raises:
        HTTPException: If test file not found
    """
    db_test_file = crud_test_file.get_test_file(db, test_file_id)
    if not db_test_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test file not found"
        )
    
    testcase_count = len(db_test_file.testcases)
    
    response = TestFileDetailResponse(
        id=db_test_file.id,
        name=db_test_file.name,
        description=db_test_file.description,
        storage_path=db_test_file.storage_path,
        created_at=db_test_file.created_at,
        updated_at=db_test_file.updated_at,
        testcase_count=testcase_count
    )
    return response


# PUBLIC_INTERFACE
@router.put("/{test_file_id}", response_model=TestFileResponse,
            summary="Update test file metadata",
            description="Update name and description of a test file.")
async def update_test_file(
    test_file_id: int,
    test_file_update: TestFileUpdate,
    db: Session = Depends(get_db)
) -> TestFileResponse:
    """
    Update test file metadata.
    
    Args:
        test_file_id: Test file ID
        test_file_update: Update data
        db: Database session
        
    Returns:
        TestFileResponse: Updated test file
        
    Raises:
        HTTPException: If test file not found
    """
    db_test_file = crud_test_file.update_test_file(db, test_file_id, test_file_update)
    if not db_test_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test file not found"
        )
    return db_test_file


# PUBLIC_INTERFACE
@router.delete("/{test_file_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Delete a test file",
               description="Delete a test file and all associated testcases, variables, and runs.")
async def delete_test_file(
    test_file_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a test file.
    
    Args:
        test_file_id: Test file ID
        db: Database session
        
    Raises:
        HTTPException: If test file not found
    """
    db_test_file = crud_test_file.get_test_file(db, test_file_id)
    if not db_test_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test file not found"
        )
    
    # Delete from storage
    storage_service.delete_file(db_test_file.storage_path)
    
    # Delete from database (cascade will handle related records)
    crud_test_file.delete_test_file(db, test_file_id)
    
    return None
