# robot_runner.py
"""Robot Framework runner module.

Runs .robot tests from byte content, stores artifacts in MinIO,
and persists run summary and per-test results to the database.
"""
import logging
import os
import json
import time
import traceback
import tempfile
from typing import Optional, Dict, List, Tuple

from robot import run as robot_run
from robot.api import ExecutionResult
from minio.error import S3Error

from db import execute
import minio_client

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)


def run_tests_background(
    run_id: str,
    minio_bytes: bytes,
    filename: str,
    variables: Optional[Dict[str, str]] = None,
    tests: Optional[List[str]] = None,
) -> None:
    """Run a Robot Framework suite from bytes, upload artifacts to MinIO,
    and persist minimal results to the DB.

    This function is intended to run inside BackgroundTasks (thread).
    """
    try:
        print(f"[RUNNER] Starting background run for ID={run_id}, file={filename}")
        _mark_run_status(run_id, "running")

        with tempfile.TemporaryDirectory() as tmpdir:
            robot_path = _write_robot_file(tmpdir, filename, minio_bytes)
            variable_list = _prepare_variable_list(variables)
            output_path, log_path, report_path = _run_robot(
                robot_path, variable_list, tests, tmpdir
            )

            # parse summary (defensive)
            try:
                summary = _parse_results(output_path)
            except (FileNotFoundError, RuntimeError, ValueError) as exc:
                LOG.exception("[RUNNER] Failed to parse ExecutionResult; "
                              "continuing with partial summary: %s", exc)
                summary = {"error": f"Parse error: {exc}"}

            # upload artifacts (best-effort)
            try:
                artifacts = _upload_artifacts(run_id, output_path, log_path,
                                              report_path)
            except (OSError, S3Error) as exc:
                LOG.exception("[RUNNER] Artifact upload failed: %s", exc)
                artifacts = {}

            # insert per-test results (best-effort)
            try:
                _insert_test_results(run_id, output_path)
            except (FileNotFoundError, RuntimeError, ValueError) as exc:
                LOG.exception("[RUNNER] Inserting per-test results failed; "
                              "continuing: %s", exc)

            # finalize run (update DB), tolerate missing artifacts column
            try:
                _finalize_run(run_id, summary, artifacts)
            except (OSError, RuntimeError) as exc:
                trace = traceback.format_exc()
                LOG.exception("[RUNNER] Finalizing run failed: %s", exc)
                try:
                    execute(
                        "UPDATE runs SET status='failed', finished_at=now(), "
                        "summary=%s WHERE id=%s",
                        (json.dumps({"error": "finalize_failed", "trace": trace}),
                         run_id),
                    )
                except (OSError, RuntimeError, ValueError):
                    LOG.exception("[RUNNER] Also failed to mark run as failed in DB")

    except (FileNotFoundError, S3Error) as exc:
        # Specific expected errors (missing output.xml or MinIO S3 issues)
        trace = traceback.format_exc()
        LOG.exception("[RUNNER] Known error during run %s: %s", run_id, exc)
        try:
            execute(
                "UPDATE runs SET status='failed', finished_at=now(), summary=%s "
                "WHERE id=%s",
                (json.dumps({"error": str(exc), "trace": trace}), run_id),
            )
        except (OSError, RuntimeError, ValueError):
            LOG.exception("[RUNNER] Failed to update DB for known error")
    except (OSError, RuntimeError, ValueError) as exc:
        # Catch common runtime/io errors and ensure DB is updated and we log the issue
        trace = traceback.format_exc()
        LOG.exception("[RUNNER] Unexpected error during run %s: %s", run_id, exc)
        try:
            execute(
                "UPDATE runs SET status='failed', finished_at=now(), summary=%s "
                "WHERE id=%s",
                (json.dumps({"error": str(exc), "trace": trace}), run_id),
            )
        except (OSError, RuntimeError, ValueError):
            LOG.exception("[RUNNER] Failed to update DB for unexpected error")


# ---- helpers -----------------------------------------------------------------


def _mark_run_status(run_id: str, status: str) -> None:
    """Update the run status and started_at timestamp (if running)."""
    try:
        if status == "running":
            execute(
                "UPDATE runs SET status=%s, started_at=now() WHERE id=%s",
                (status, run_id),
            )
        else:
            execute("UPDATE runs SET status=%s WHERE id=%s", (status, run_id))
    except (OSError, RuntimeError, ValueError) as exc:
        LOG.exception("[RUNNER] Failed to mark run status in DB: %s", exc)


def _write_robot_file(tmpdir: str, filename: str, content: bytes) -> str:
    """Write the .robot content to a temporary file and return its path."""
    path = os.path.join(tmpdir, filename)
    with open(path, "wb") as fh:
        fh.write(content or b"")
    print(f"[RUNNER] Saved robot file to {path} (temp)")
    return path


def _prepare_variable_list(variables: Optional[Dict[str, str]]) -> Optional[List[str]]:
    """Convert variables dict to Robot Framework CLI variable list (NAME:VALUE)."""
    if not variables:
        return None

    result: List[str] = []
    for k, v in variables.items():
        v = "" if v is None else v
        result.append(f"{k}:{v}")
    return result


def _run_robot(
    robot_path: str,
    variable_list: Optional[List[str]],
    tests: Optional[List[str]],
    tmpdir: str,
) -> Tuple[str, str, str]:
    """Run the robot suite using Robot Framework API.

    Returns (output, log, report) paths. Raises FileNotFoundError if output.xml
    is not produced.
    """
    output_path = os.path.join(tmpdir, "output.xml")
    log_path = os.path.join(tmpdir, "log.html")
    report_path = os.path.join(tmpdir, "report.html")

    LOG.info("[RUNNER] Running Robot Framework...")
    # robot_run returns exit code
    rc = robot_run(
        robot_path,
        output=output_path,
        log=log_path,
        report=report_path,
        outputdir=tmpdir,
        console="none",
        variable=variable_list,
        test=tests if tests else None,
    )
    LOG.info("[RUNNER] Robot Framework finished with rc=%s", rc)

    # Wait shortly for files to appear (robot might write them after return)
    for _ in range(10):
        if os.path.exists(output_path):
            break
        time.sleep(0.2)

    if not os.path.exists(output_path):
        raise FileNotFoundError(
            f"output.xml not found in temporary dir {tmpdir}"
        )

    return output_path, log_path, report_path


def _parse_results(output_path: str) -> Dict[str, Optional[int]]:
    """Parse Robot output.xml into a minimal summary dict.

    Defensive: if parsing fails, raise exception to be handled by caller.
    """
    result = ExecutionResult(output_path)
    stats = getattr(result, "statistics", None)
    total = getattr(getattr(stats, "total", None), "all", None) if stats else None
    passed = getattr(getattr(stats, "total", None), "passed", None) if stats else None
    failed = getattr(getattr(stats, "total", None), "failed", None) if stats else None
    return_code = getattr(result, "return_code", None)

    summary = {
        "total": total,
        "passed": passed,
        "failed": failed,
        "return_code": return_code,
    }
    LOG.info("[RUNNER] Parsed summary: %s", summary)
    return summary


def _upload_artifacts(
    run_id: str, output_path: str, log_path: str, report_path: str
) -> Dict[str, str]:
    """Upload output/log/report files to MinIO and return artifact key mapping.

    Returns an empty dict if none uploaded.
    """
    prefix = f"runs/{run_id}"
    artifacts: Dict[str, str] = {}

    def _maybe_upload(file_path: str, key_suffix: str, content_type: str) -> None:
        if os.path.exists(file_path):
            with open(file_path, "rb") as fh:
                data = fh.read()
            key = f"{prefix}/{key_suffix}"
            # minio_client.put_bytes should write the bytes to MinIO
            minio_client.put_bytes(key, data, content_type=content_type)
            artifacts[key_suffix.split(".")[0]] = key
            LOG.info("[RUNNER] Uploaded artifact %s -> %s", file_path, key)
        else:
            LOG.debug("[RUNNER] Artifact %s not found; skipping upload", file_path)

    _maybe_upload(output_path, "output.xml", "application/xml")
    _maybe_upload(log_path, "log.html", "text/html")
    _maybe_upload(report_path, "report.html", "text/html")

    return artifacts


def _insert_test_results(run_id: str, output_path: str) -> None:
    """Insert per-test results into test_results table.

    If ExecutionResult parsing fails, logs exception and returns.
    """
    try:
        result = ExecutionResult(output_path)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        LOG.exception("[RUNNER] ExecutionResult parsing failed while inserting "
                      "test results: %s", exc)
        return

    def _insert_suite(suite) -> None:
        for t in getattr(suite, "tests", []):
            try:
                execute(
                    "INSERT INTO test_results (run_id, case_name, status, message, "
                    "duration_ms) VALUES (%s,%s,%s,%s,%s)",
                    (
                        run_id,
                        t.name,
                        getattr(t, "status", None),
                        getattr(t, "message", "") or "",
                        getattr(t, "elapsedtime", None),
                    ),
                )
            except (OSError, RuntimeError, ValueError):
                LOG.exception("[RUNNER] Failed to insert test result for case %s: %s",
                              getattr(t, "name", "<unknown>"), exc)

        for child in getattr(suite, "suites", []):
            _insert_suite(child)

    _insert_suite(result.suite)


def _finalize_run(run_id: str, summary: Dict[str, Optional[int]], artifacts: Dict[str, str]) -> None:
    """Mark run completed and store summary/artifacts.

    Try primary UPDATE including artifacts; on failure try fallback UPDATE
    without artifacts. Always swallow exceptions (but log them) so callers
    don't raise for best-effort persistence.
    """
    try:
        execute(
            "UPDATE runs SET status='completed', finished_at=now(), summary=%s, "
            "artifacts=%s WHERE id=%s",
            (json.dumps(summary), json.dumps(artifacts), run_id),
        )
        LOG.info(
            "[RUNNER] ✅ Run %s marked completed and artifacts uploaded: %s",
            run_id,
            artifacts,
        )
        return
    except Exception as exc:  # best-effort: log and attempt fallback
        LOG.exception(
            "[RUNNER] Failed to update runs with artifacts; attempting fallback without artifacts: %s",
            exc,
        )

    # Fallback: try to update without artifacts
    try:
        execute(
            "UPDATE runs SET status='completed', finished_at=now(), summary=%s WHERE id=%s",
            (json.dumps(summary), run_id),
        )
        LOG.info(
            "[RUNNER] ✅ Run %s marked completed (no artifacts persisted)",
            run_id,
        )
    except Exception as exc2:
        # Log the fallback failure but do not raise — keep behavior best-effort.
        LOG.exception("[RUNNER] Failed to finalize run in DB (fallback): %s", exc2)
