"""
API routes for test file management.
Provides endpoints for uploading, managing, and retrieving robot test files.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Dict, Any, Union
import tempfile
import os
import uuid
import logging
from urllib.parse import unquote

from core.database import get_db
from schemas.test_file import TestFileResponse, TestFileDetailResponse, TestFileUpdate
from crud import test_file as crud_test_file
from crud import testcase as crud_testcase
from crud import input_variable as crud_input_variable
from services.robot_parser import robot_parser
from services.storage_service import save_robot_file, generate_unique_storage_path, get_robot_file
from core.storage import storage_service
from robot_schema import get_required_variables_for_case

router = APIRouter(prefix="/tests", tags=["Test Files"])
logger = logging.getLogger(__name__)


def _decode_robot_file_content(file_content_bytes: bytes, file_path: str = "") -> str:
    """
    Decode robot file content with robust encoding detection.
    
    Tries UTF-8 first, then uses charset-normalizer to detect encoding,
    and falls back to UTF-8 with replacement as last resort.
    
    Args:
        file_content_bytes: Raw file content bytes
        file_path: Optional file path for logging
        
    Returns:
        str: Decoded file content
    """
    # Try UTF-8 first (most common)
    try:
        return file_content_bytes.decode('utf-8')
    except UnicodeDecodeError:
        pass
    
    # Try charset-normalizer for automatic detection
    try:
        from charset_normalizer import from_bytes
        result = from_bytes(file_content_bytes).best()
        if result and result.encoding:
            logger.info(f"Detected encoding {result.encoding} for file {file_path}")
            return str(result)
    except Exception as e:
        logger.warning(f"charset-normalizer detection failed for {file_path}: {e}")
    
    # Last resort: UTF-8 with replacement
    logger.warning(f"Using UTF-8 with replacement for {file_path}")
    return file_content_bytes.decode('utf-8', errors='replace')


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
    
    Handles duplicate storage paths by generating unique paths with UUID suffixes.
    
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
        
        # Parse testcases and variables (now returns 3-tuple)
        parsed = robot_parser.parse_file(tmp_file_path)
        if isinstance(parsed, tuple) and len(parsed) == 3:
            testcases, file_level_variables, testcase_level_variables = parsed
        else:
            # Backward compatibility (should not happen after parser update)
            testcases, file_level_variables = parsed  # type: ignore
            testcase_level_variables = {}

        # Strategy for handling duplicates:
        # 1. Create test file record first with a temporary unique storage path using UUID
        # 2. Upload to storage with actual ID
        # 3. Update storage path
        # 4. If collision still occurs (rare), retry with new UUID
        
        from schemas.test_file import TestFileCreate
        
        max_retries = 3
        db_test_file = None
        
        for attempt in range(max_retries):
            # Generate a unique temporary storage path
            temp_storage_path = f"pending_{uuid.uuid4().hex[:12]}_{file.filename}"
            
            test_file_create = TestFileCreate(name=file.filename, description=None)
            db_test_file = crud_test_file.create_test_file_safe(
                db,
                test_file_create,
                temp_storage_path
            )
            
            if db_test_file:
                break
            
            # If we still get a duplicate (very unlikely), try again
            if attempt == max_retries - 1:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create unique record after multiple attempts"
                )
        
        if not db_test_file:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create test file record"
            )
        
        # Now we have a DB record with an ID, generate the final storage path
        # Check if a file with this final path already exists
        final_storage_path = generate_unique_storage_path(db_test_file.id, file.filename, add_uuid=False)
        existing_file = crud_test_file.get_test_file_by_storage_path(db, final_storage_path)
        
        if existing_file and existing_file.id != db_test_file.id:
            # Path collision with another file, add UUID to make it unique
            final_storage_path = generate_unique_storage_path(db_test_file.id, file.filename, add_uuid=True)
        
        # Upload to storage with the final path
        try:
            storage_path = save_robot_file(file_content, db_test_file.id, 
                                         final_storage_path.split('/')[-1])
        except Exception as e:
            # Clean up database record if storage fails
            crud_test_file.delete_test_file(db, db_test_file.id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload file to storage: {str(e)}"
            )
        
        # Update storage path with retry logic for integrity errors
        max_update_retries = 3
        update_success = False
        
        for update_attempt in range(max_update_retries):
            try:
                db_test_file.storage_path = storage_path
                db.commit()
                db.refresh(db_test_file)
                update_success = True
                break
            except IntegrityError:
                db.rollback()
                # Generate a new unique path and try again
                storage_path = save_robot_file(
                    file_content, 
                    db_test_file.id, 
                    generate_unique_storage_path(db_test_file.id, file.filename, add_uuid=True).split('/')[-1]
                )
        
        if not update_success:
            # Clean up database and storage
            crud_test_file.delete_test_file(db, db_test_file.id)
            try:
                storage_service.delete_file(storage_path)
            except:
                pass
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update storage path after multiple attempts"
            )
        
        # Create testcases, then build name->id map
        created_tcs = crud_testcase.create_testcases_bulk(db, testcases, db_test_file.id)
        name_to_id: Dict[str, int] = {tc.name: tc.id for tc in created_tcs}

        # Create file-level variables (no testcase_id)
        if file_level_variables:
            crud_input_variable.create_variables_bulk(db, file_level_variables, db_test_file.id)

        # Create testcase-level variables with testcase_id mapping
        for tc_name, vars_list in (testcase_level_variables or {}).items():
            tc_id = name_to_id.get(tc_name)
            if tc_id and vars_list:
                crud_input_variable.create_variables_bulk(db, vars_list, db_test_file.id, testcase_id=tc_id)
        
        # Return response
        response = TestFileDetailResponse(
            id=db_test_file.id,
            test_uid=db_test_file.test_uid,
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
        test_uid=db_test_file.test_uid,
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


# PUBLIC_INTERFACE
@router.get("/{test_identifier}/testcases/{case_identifier}/required-variables",
            response_model=Dict[str, Any],
            summary="Get required variables for a test case",
            description="Analyze a test case and return the list of required input variables. Accepts both integer IDs and UUIDs for test and testcase identifiers.")
async def get_testcase_required_variables(
    test_identifier: Union[int, str],
    case_identifier: Union[int, str],
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get required variables for a specific test case.
    
    This endpoint retrieves the robot file content, parses it, and analyzes
    the specified test case to determine which variables are required as inputs.
    
    Variables that are assigned within the test case or its called keywords
    are excluded from the result.
    
    Supports both legacy paths (with integer IDs and case names) and new paths
    (with UUIDs). The test_identifier can be an integer test_id or a UUID test_uid.
    The case_identifier can be an integer testcase_id, UUID testcase_uid, or case_name.
    
    Args:
        test_identifier: Test file ID (int), test_uid (UUID string), or legacy test_id
        case_identifier: Test case ID (int), testcase_uid (UUID string), or case_name (str)
        db: Database session
        
    Returns:
        Dict containing:
            - test_id: Test file ID
            - test_uid: Test file UUID
            - testcase_id: Test case ID (if resolved)
            - testcase_uid: Test case UUID (if resolved)
            - case_name: Test case name
            - required_variables: List of required variable names
            
    Raises:
        HTTPException: 
            - 400 if identifiers are invalid
            - 404 if test file or test case not found
            - 500 if analysis fails
    """
    # Resolve test file
    db_test_file = None
    
    # Try to parse as UUID first
    try:
        from uuid import UUID
        test_uid = UUID(str(test_identifier))
        db_test_file = crud_test_file.get_test_file_by_uid(db, test_uid)
    except (ValueError, TypeError):
        # Not a UUID, try as integer ID
        try:
            test_id = int(test_identifier)
            db_test_file = crud_test_file.get_test_file(db, test_id)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid test_identifier: must be an integer ID or UUID"
            )
    
    if not db_test_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test file with identifier {test_identifier} not found"
        )
    
    # Resolve test case
    db_testcase = None
    case_name = None
    
    # Try to parse as UUID first
    try:
        from uuid import UUID
        testcase_uid = UUID(str(case_identifier))
        db_testcase = crud_testcase.get_testcase_by_uid(db, testcase_uid)
        if db_testcase:
            case_name = db_testcase.name
            # Verify it belongs to the correct test file
            if db_testcase.test_file_id != db_test_file.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Test case does not belong to the specified test file"
                )
    except (ValueError, TypeError):
        # Not a UUID, try as integer ID
        try:
            testcase_id = int(case_identifier)
            db_testcase = crud_testcase.get_testcase(db, testcase_id)
            if db_testcase:
                case_name = db_testcase.name
                # Verify it belongs to the correct test file
                if db_testcase.test_file_id != db_test_file.id:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Test case does not belong to the specified test file"
                    )
        except (ValueError, TypeError):
            # Treat as case name (string)
            case_name = unquote(str(case_identifier))
            # Try to find by name
            db_testcase = crud_testcase.get_testcase_by_name(db, db_test_file.id, case_name)
    
    # Validate case_name
    if not case_name or not case_name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid case_identifier parameter"
        )
    
    # Retrieve robot file content from storage with robust encoding
    try:
        file_content_bytes = get_robot_file(db_test_file.storage_path)
        if file_content_bytes is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Test file content not found in storage: {db_test_file.storage_path}"
            )
        
        # Decode with robust encoding detection
        file_content = _decode_robot_file_content(file_content_bytes, db_test_file.storage_path)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve/decode test file content: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve test file content: {str(e)}"
        )
    
    # Analyze the test case for required variables
    try:
        result = get_required_variables_for_case(
            content=file_content,
            case_name=case_name,
            test_id=db_test_file.id
        )
        
        # Enhance result with additional identifiers
        result["test_uid"] = str(db_test_file.test_uid)
        if db_testcase:
            result["testcase_id"] = db_testcase.id
            result["testcase_uid"] = str(db_testcase.testcase_uid)
        
        return result
        
    except ValueError as e:
        # Test case not found
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to analyze test case: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze test case: {str(e)}"
        )
