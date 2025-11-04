"""
Additional API routes for group-based run management.

This module is imported by api.routes.runs to register endpoints for:
- Listing groups
- Listing runs within a group
- Queue-start all queued runs for a group
"""
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from core.database import get_db
from models.run import Run, RunStatus
from crud import run as crud_run
from crud import test_file as crud_test_file
from crud import testcase as crud_testcase
from crud import run_config as crud_run_config
from services.storage_service import save_run_artifact
from services.robot_executor import robot_executor
from core.storage import storage_service
import tempfile
import os
import shutil

router = APIRouter(prefix="/runs", tags=["Test Runs"])

def _collect_unique_cases_for_group(db: Session, group_id: str) -> List[str]:
    """Collect distinct testcase names present in runs for the group."""
    case_names = set()
    # For testcase runs, load testcase name; for file runs, leave as file-level indicator
    runs = db.query(Run).filter(Run.group_id == group_id).all()
    for r in runs:
        if r.testcase_id:
            tc = crud_testcase.get_testcase(db, r.testcase_id)
            if tc:
                case_names.add(tc.name)
    return sorted(list(case_names))

# PUBLIC_INTERFACE
@router.get("/groups", summary="List run groups", description="Return groups aggregated by group_id with counts and timestamps")
def list_run_groups(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """List groups with aggregate info and testcase listing."""
    # Query aggregates
    rows = db.query(
        Run.group_id,
        Run.group_name,
    ).filter(Run.group_id.isnot(None)).distinct().all()

    results: List[Dict[str, Any]] = []
    for gid, gname in rows:
        # compute aggregate values
        group_runs = db.query(Run).filter(Run.group_id == gid).all()
        if not group_runs:
            continue
        run_count = len(group_runs)
        first_created = min(r.created_at for r in group_runs)
        last_created = max(r.created_at for r in group_runs)
        testcases = _collect_unique_cases_for_group(db, gid)
        results.append({
            "group_id": gid,
            "group_name": gname or "",
            "run_count": run_count,
            "first_created": first_created,
            "last_created": last_created,
            "testcases": testcases
        })
    # Order by last_created desc
    results.sort(key=lambda x: x["last_created"], reverse=True)
    return results

# PUBLIC_INTERFACE
@router.get("/groups/{group_id}", summary="Get runs by group", description="Return runs for a given group_id")
def get_runs_by_group(group_id: str, db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """Return detailed runs for a group."""
    runs = db.query(Run).filter(Run.group_id == group_id).order_by(Run.created_at.desc()).all()
    results = []
    for r in runs:
        results.append({
            "id": r.id,
            "test_file_id": r.test_file_id,
            "testcase_id": r.testcase_id,
            "run_config_id": r.run_config_id,
            "group_id": r.group_id,
            "group_name": r.group_name,
            "status": r.status,
            "created_at": r.created_at,
            "started_at": r.started_at,
            "completed_at": r.completed_at,
            "log_path": r.log_path,
            "output_path": r.output_path,
            "report_path": r.report_path,
            "error_message": r.error_message
        })
    return results

def _execute_test_run_internal(run_id: int, db: Session) -> None:
    """Reuse logic similar to execute_test_run in runs.py to start execution."""
    from core.database import SessionLocal
    # local session for background
    local_db = SessionLocal()
    try:
        run = crud_run.get_run(local_db, run_id)
        if not run:
            return
        # Determine test file and optional testcase
        testcase_name = None
        if run.testcase_id:
            tc = crud_testcase.get_testcase(local_db, run.testcase_id)
            testcase_name = tc.name if tc else None
            test_file_id = tc.test_file_id if tc else run.test_file_id
        else:
            test_file_id = run.test_file_id

        db_test_file = crud_test_file.get_test_file(local_db, test_file_id)
        if not db_test_file:
            crud_run.update_run_status(local_db, run_id, RunStatus.ERROR, error_message="Test file not found")
            return
        file_content = storage_service.get_file(db_test_file.storage_path)
        if not file_content:
            crud_run.update_run_status(local_db, run_id, RunStatus.ERROR, error_message="Failed to retrieve test file")
            return

        # write temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".robot") as tmp_file:
            tmp_file.write(file_content)
            tmp_file_path = tmp_file.name

        # Fetch run_config for tags/timeout/variables
        include_tags = None
        exclude_tags = None
        timeout = None
        variables = {}

        if run.run_config_id:
            cfg = crud_run_config.get_run_config(local_db, run.run_config_id)
            if cfg:
                include_tags = cfg.include_tags
                exclude_tags = cfg.exclude_tags
                timeout = cfg.timeout
                variables = cfg.variables or {}

        # Start execution updating status
        crud_run.update_run_status(local_db, run_id, RunStatus.RUNNING)
        if testcase_name:
            return_code, log_path, output_path, report_path = robot_executor.execute_testcase(
                tmp_file_path, testcase_name, variables, timeout
            )
        else:
            return_code, log_path, output_path, report_path = robot_executor.execute_test_file(
                tmp_file_path, variables, include_tags, exclude_tags, timeout
            )

        # Save artifacts
        log_storage_path = save_run_artifact(log_path, run_id, "log")
        output_storage_path = save_run_artifact(output_path, run_id, "output")
        report_storage_path = save_run_artifact(report_path, run_id, "report")

        final_status = RunStatus.PASSED if return_code == 0 else RunStatus.FAILED
        crud_run.update_run_status(
            local_db, run_id, final_status,
            log_path=log_storage_path,
            output_path=output_storage_path,
            report_path=report_storage_path
        )
        # Cleanup temp dir
        try:
            tmp_dir = os.path.dirname(log_path)
            if os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir, ignore_errors=True)
        finally:
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
    except Exception as e:
        try:
            crud_run.update_run_status(local_db, run_id, RunStatus.ERROR, error_message=str(e))
        finally:
            pass
    finally:
        local_db.close()

# PUBLIC_INTERFACE
@router.post("/groups/{group_id}/queuestart", summary="Execute all queued runs in a group", description="Schedule all queued runs for the specified group_id")
def queuestart_group_runs(group_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Queue start all runs with status=queued in the group."""
    queued_runs = db.query(Run).filter(Run.group_id == group_id, Run.status == RunStatus.QUEUED).order_by(Run.created_at.asc()).all()
    if not queued_runs:
        return {"group_id": group_id, "scheduled": 0, "message": "No queued runs found"}

    for r in queued_runs:
        background_tasks.add_task(_execute_test_run_internal, r.id, db)

    return {"group_id": group_id, "scheduled": len(queued_runs)}
