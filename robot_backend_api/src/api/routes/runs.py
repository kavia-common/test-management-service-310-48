"""
API routes for test run management and execution.
Provides endpoints for executing robot tests and retrieving run results.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session
from typing import List, Optional
import tempfile
import os
import shutil

from ...core.database import get_db
from ...schemas.run import (
    RunResponse, RunCreate, RunTestCaseRequest,
    RunQueueExecuteRequest, RunLogsResponse
)
from ...models.run import RunStatus
from ...crud import run as crud_run
from ...crud import test_file as crud_test_file
from ...crud import testcase as crud_testcase
from ...crud import run_config as crud_run_config
from ...services.robot_executor import robot_executor
from ...services.storage_service import save_run_artifact
from ...core.storage import storage_service

router = APIRouter(prefix="/runs", tags=["Test Runs"])


def execute_test_run(run_id: int, robot_file_path: str, testcase_name: Optional[str],
                     variables: Optional[dict], include_tags: Optional[str],
                     exclude_tags: Optional[str], timeout: Optional[int]):
    """
    Background task to execute a test run.
    
    Args:
        run_id: Run ID
        robot_file_path: Path to robot test file
        testcase_name: Optional testcase name for specific testcase execution
        variables: Robot variables
        include_tags: Tags to include
        exclude_tags: Tags to exclude
        timeout: Execution timeout
    """
    from ...core.database import SessionLocal
    
    db = SessionLocal()
    try:
        # Update status to running
        crud_run.update_run_status(db, run_id, RunStatus.RUNNING)
        
        # Execute test
        if testcase_name:
            return_code, log_path, output_path, report_path = robot_executor.execute_testcase(
                robot_file_path, testcase_name, variables, timeout
            )
        else:
            return_code, log_path, output_path, report_path = robot_executor.execute_test_file(
                robot_file_path, variables, include_tags, exclude_tags, timeout
            )
        
        # Save artifacts to storage
        log_storage_path = save_run_artifact(log_path, run_id, "log")
        output_storage_path = save_run_artifact(output_path, run_id, "output")
        report_storage_path = save_run_artifact(report_path, run_id, "report")
        
        # Update run status based on return code
        final_status = RunStatus.PASSED if return_code == 0 else RunStatus.FAILED
        crud_run.update_run_status(
            db, run_id, final_status,
            log_path=log_storage_path,
            output_path=output_storage_path,
            report_path=report_storage_path
        )
        
        # Cleanup temp files
        temp_dir = os.path.dirname(log_path)
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        
    except Exception as e:
        # Update run status to error
        crud_run.update_run_status(db, run_id, RunStatus.ERROR, error_message=str(e))
    finally:
        # Cleanup robot file
        if os.path.exists(robot_file_path):
            os.unlink(robot_file_path)
        db.close()


# PUBLIC_INTERFACE
@router.post("/", response_model=RunResponse, status_code=status.HTTP_201_CREATED,
             summary="Create and execute a test run for a complete file",
             description="Execute all tests in a robot test file. Execution happens in the background.")
async def create_run(
    run_create: RunCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
) -> RunResponse:
    """
    Create and execute a test run for a complete file.
    
    Args:
        run_create: Run creation data
        background_tasks: FastAPI background tasks
        db: Database session
        
    Returns:
        RunResponse: Created run
        
    Raises:
        HTTPException: If test file not found or validation fails
    """
    # Validate test file exists
    if not run_create.test_file_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="test_file_id is required"
        )
    
    db_test_file = crud_test_file.get_test_file(db, run_create.test_file_id)
    if not db_test_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test file not found"
        )
    
    # Get run config if specified
    include_tags = None
    exclude_tags = None
    timeout = None
    config_variables = {}
    
    if run_create.run_config_id:
        db_config = crud_run_config.get_run_config(db, run_create.run_config_id)
        if db_config:
            include_tags = db_config.include_tags
            exclude_tags = db_config.exclude_tags
            timeout = db_config.timeout
            config_variables = db_config.variables or {}
    
    # Merge variables
    merged_variables = {**config_variables, **(run_create.variables or {})}
    
    # Create run record
    db_run = crud_run.create_run(db, run_create)
    
    # Download robot file to temp location
    file_content = storage_service.get_file(db_test_file.storage_path)
    if not file_content:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve test file from storage"
        )
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.robot') as tmp_file:
        tmp_file.write(file_content)
        tmp_file_path = tmp_file.name
    
    # Execute in background
    background_tasks.add_task(
        execute_test_run,
        db_run.id,
        tmp_file_path,
        None,
        merged_variables,
        include_tags,
        exclude_tags,
        timeout
    )
    
    return db_run


# PUBLIC_INTERFACE
@router.post("/testcase", response_model=RunResponse, status_code=status.HTTP_201_CREATED,
             summary="Execute a specific testcase",
             description="Execute a single testcase from a robot test file. Execution happens in the background.")
async def run_testcase(
    request: RunTestCaseRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
) -> RunResponse:
    """
    Execute a specific testcase.
    
    Args:
        request: Testcase run request
        background_tasks: FastAPI background tasks
        db: Database session
        
    Returns:
        RunResponse: Created run
        
    Raises:
        HTTPException: If testcase not found or validation fails
    """
    # Validate testcase exists
    db_testcase = crud_testcase.get_testcase(db, request.testcase_id)
    if not db_testcase:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test case not found"
        )
    
    # Get test file
    db_test_file = crud_test_file.get_test_file(db, db_testcase.test_file_id)
    if not db_test_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test file not found"
        )
    
    # Get run config if specified
    timeout = None
    config_variables = {}
    
    if request.run_config_id:
        db_config = crud_run_config.get_run_config(db, request.run_config_id)
        if db_config:
            timeout = db_config.timeout
            config_variables = db_config.variables or {}
    
    # Merge variables
    merged_variables = {**config_variables, **(request.variables or {})}
    
    # Create run record
    run_create = RunCreate(
        test_file_id=db_testcase.test_file_id,
        testcase_id=request.testcase_id,
        run_config_id=request.run_config_id
    )
    db_run = crud_run.create_run(db, run_create)
    
    # Download robot file to temp location
    file_content = storage_service.get_file(db_test_file.storage_path)
    if not file_content:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve test file from storage"
        )
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.robot') as tmp_file:
        tmp_file.write(file_content)
        tmp_file_path = tmp_file.name
    
    # Execute in background
    background_tasks.add_task(
        execute_test_run,
        db_run.id,
        tmp_file_path,
        db_testcase.name,
        merged_variables,
        None,
        None,
        timeout
    )
    
    return db_run


# PUBLIC_INTERFACE
@router.get("/", response_model=List[RunResponse],
            summary="List all test runs",
            description="Retrieve a paginated list of all test runs, optionally filtered by status.")
async def list_runs(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[RunStatus] = None,
    db: Session = Depends(get_db)
) -> List[RunResponse]:
    """
    List all test runs.
    
    Args:
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        status_filter: Optional status filter
        db: Database session
        
    Returns:
        List[RunResponse]: List of runs
    """
    runs = crud_run.get_runs(db, skip=skip, limit=limit, status=status_filter)
    return runs


# PUBLIC_INTERFACE
@router.get("/{run_id}", response_model=RunResponse,
            summary="Get run details",
            description="Retrieve detailed information about a specific test run.")
async def get_run(
    run_id: int,
    db: Session = Depends(get_db)
) -> RunResponse:
    """
    Get run by ID.
    
    Args:
        run_id: Run ID
        db: Database session
        
    Returns:
        RunResponse: Run details
        
    Raises:
        HTTPException: If run not found
    """
    db_run = crud_run.get_run(db, run_id)
    if not db_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found"
        )
    return db_run


# PUBLIC_INTERFACE
@router.get("/{run_id}/logs", response_model=RunLogsResponse,
            summary="Get run logs and artifacts",
            description="Retrieve presigned URLs for log, output.xml, and report.html files.")
async def get_run_logs(
    run_id: int,
    db: Session = Depends(get_db)
) -> RunLogsResponse:
    """
    Get run logs and artifact URLs.
    
    Args:
        run_id: Run ID
        db: Database session
        
    Returns:
        RunLogsResponse: Presigned URLs for artifacts
        
    Raises:
        HTTPException: If run not found or not completed
    """
    db_run = crud_run.get_run(db, run_id)
    if not db_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found"
        )
    
    if db_run.status not in [RunStatus.PASSED, RunStatus.FAILED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Run has not completed yet"
        )
    
    # Get presigned URLs
    log_url = None
    output_url = None
    report_url = None
    log_content = None
    
    if db_run.log_path:
        log_url = storage_service.get_presigned_url(db_run.log_path)
        # Also get log content
        log_data = storage_service.get_file(db_run.log_path)
        if log_data:
            log_content = log_data.decode('utf-8', errors='ignore')
    
    if db_run.output_path:
        output_url = storage_service.get_presigned_url(db_run.output_path)
    
    if db_run.report_path:
        report_url = storage_service.get_presigned_url(db_run.report_path)
    
    return RunLogsResponse(
        run_id=run_id,
        log_content=log_content,
        log_url=log_url,
        output_url=output_url,
        report_url=report_url
    )


# PUBLIC_INTERFACE
@router.post("/queue/execute", response_model=List[RunResponse],
             summary="Queue batch execution",
             description="Queue multiple test files or testcases for execution using a run configuration.")
async def queue_batch_execution(
    request: RunQueueExecuteRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
) -> List[RunResponse]:
    """
    Queue batch execution of multiple tests.
    
    Args:
        request: Batch execution request
        background_tasks: FastAPI background tasks
        db: Database session
        
    Returns:
        List[RunResponse]: List of created runs
        
    Raises:
        HTTPException: If validation fails
    """
    # Validate run config exists
    db_config = crud_run_config.get_run_config(db, request.run_config_id)
    if not db_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run configuration not found"
        )
    
    created_runs = []
    
    # Queue test file runs
    if request.test_file_ids:
        for test_file_id in request.test_file_ids:
            run_create = RunCreate(
                test_file_id=test_file_id,
                run_config_id=request.run_config_id
            )
            try:
                run_response = await create_run(run_create, background_tasks, db)
                created_runs.append(run_response)
            except HTTPException:
                # Skip invalid files
                pass
    
    # Queue testcase runs
    if request.testcase_ids:
        for testcase_id in request.testcase_ids:
            testcase_request = RunTestCaseRequest(
                testcase_id=testcase_id,
                run_config_id=request.run_config_id
            )
            try:
                run_response = await run_testcase(testcase_request, background_tasks, db)
                created_runs.append(run_response)
            except HTTPException:
                # Skip invalid testcases
                pass
    
    return created_runs
