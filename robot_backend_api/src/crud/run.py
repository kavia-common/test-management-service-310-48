"""
CRUD operations for test runs.
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from ..models.run import Run, RunStatus
from ..schemas.run import RunCreate


# PUBLIC_INTERFACE
def get_run(db: Session, run_id: int) -> Optional[Run]:
    """
    Get a run by ID.
    
    Args:
        db: Database session
        run_id: Run ID
        
    Returns:
        Optional[Run]: Run if found, None otherwise
    """
    return db.query(Run).filter(Run.id == run_id).first()


# PUBLIC_INTERFACE
def get_runs(db: Session, skip: int = 0, limit: int = 100, status: Optional[RunStatus] = None) -> List[Run]:
    """
    Get a list of runs, optionally filtered by status.
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        status: Filter by status
        
    Returns:
        List[Run]: List of runs
    """
    query = db.query(Run)
    if status:
        query = query.filter(Run.status == status)
    return query.order_by(Run.created_at.desc()).offset(skip).limit(limit).all()


# PUBLIC_INTERFACE
def create_run(db: Session, run: RunCreate) -> Run:
    """
    Create a new run record.
    
    Args:
        db: Database session
        run: Run creation data
        
    Returns:
        Run: Created run
    """
    db_run = Run(
        test_file_id=run.test_file_id,
        testcase_id=run.testcase_id,
        run_config_id=run.run_config_id,
        status=RunStatus.QUEUED
    )
    db.add(db_run)
    db.commit()
    db.refresh(db_run)
    return db_run


# PUBLIC_INTERFACE
def update_run_status(
    db: Session,
    run_id: int,
    status: RunStatus,
    error_message: Optional[str] = None,
    log_path: Optional[str] = None,
    output_path: Optional[str] = None,
    report_path: Optional[str] = None
) -> Optional[Run]:
    """
    Update run status and related fields.
    
    Args:
        db: Database session
        run_id: Run ID
        status: New status
        error_message: Error message if failed
        log_path: Path to log file in storage
        output_path: Path to output.xml in storage
        report_path: Path to report.html in storage
        
    Returns:
        Optional[Run]: Updated run if found, None otherwise
    """
    db_run = get_run(db, run_id)
    if not db_run:
        return None
    
    db_run.status = status
    
    if status == RunStatus.RUNNING and not db_run.started_at:
        db_run.started_at = datetime.utcnow()
    
    if status in [RunStatus.PASSED, RunStatus.FAILED, RunStatus.ERROR]:
        db_run.completed_at = datetime.utcnow()
    
    if error_message:
        db_run.error_message = error_message
    
    if log_path:
        db_run.log_path = log_path
    if output_path:
        db_run.output_path = output_path
    if report_path:
        db_run.report_path = report_path
    
    db.commit()
    db.refresh(db_run)
    return db_run


# PUBLIC_INTERFACE
def get_runs_by_test_file(db: Session, test_file_id: int) -> List[Run]:
    """
    Get all runs for a specific test file.
    
    Args:
        db: Database session
        test_file_id: Test file ID
        
    Returns:
        List[Run]: List of runs
    """
    return db.query(Run).filter(Run.test_file_id == test_file_id).order_by(Run.created_at.desc()).all()


# PUBLIC_INTERFACE
def get_runs_by_testcase(db: Session, testcase_id: int) -> List[Run]:
    """
    Get all runs for a specific testcase.
    
    Args:
        db: Database session
        testcase_id: Test case ID
        
    Returns:
        List[Run]: List of runs
    """
    return db.query(Run).filter(Run.testcase_id == testcase_id).order_by(Run.created_at.desc()).all()
