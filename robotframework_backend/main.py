"""
Robot Runner Service API.

This module implements the FastAPI app used to upload Robot Framework tests,
extract variables, queue and run tests, and fetch run results.
"""

import io
import json
import uuid
from typing import Optional

from fastapi import FastAPI, Form, UploadFile, File, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware

import uvicorn
import db
import minio_client
import robot_parser
import robot_runner
import schemas
import robot_schema


app = FastAPI(title="Robot Runner Service")

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup() -> None:
    """Initialize DB connection pool on startup."""
    db.DBPool.init()

def _serialize_row_timestamps(row: dict) -> dict:
    """
    Convert datetime objects to ISO format strings in a DB row dict.

    Returns the (possibly modified) row.
    """
    if not row:
        return row
    for k, v in list(row.items()):
        if hasattr(v, "isoformat"):
            row[k] = v.isoformat()
    # ensure tags (jsonb) is a list/object and not a string
    if "tags" in row and isinstance(row["tags"], str):
        try:
            row["tags"] = json.loads(row["tags"])
        except json.JSONDecodeError:
            # If parsing fails, leave as-is to avoid breaking callers.
            pass
    return row


@app.get("/api/lexi/robot/tests")
def list_tests() -> list:
    """Return a list of uploaded tests (basic metadata)."""
    rows = db.fetchall(
        "SELECT id, name, description, filename, created_at FROM tests "
        "ORDER BY created_at DESC"
    )
    for r in rows:
        _serialize_row_timestamps(r)
    return rows

def _put_minio_object(key: str, content: bytes, content_type: str = "text/plain") -> None:
    """Upload object to MinIO and raise HTTPException on failure."""
    try:
        minio_client.put_object(key, io.BytesIO(content), len(content), content_type=content_type)
    except Exception as exc:  # MinIO client may raise various errors
        raise HTTPException(status_code=500, detail=f"MinIO error: {exc}") from exc

@app.post("/api/lexi/robot/tests/upload")
def upload_test(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(...)
    )-> dict:
    """
    Upload a .robot file, extract variables and usage, store file in MinIO,
    and create a DB record.
    """
    if not file.filename.endswith(".robot"):
        raise HTTPException(status_code=400, detail="Only .robot files are accepted")

    content = file.file.read()
    key = f"tests/{uuid.uuid4()}-{file.filename}"

    _put_minio_object(key, content, content_type="text/plain")

    name = name or file.filename
    row = db.insert_fetchone(
        "INSERT INTO tests (name, description, minio_key, filename) "
        "VALUES (%s, %s, %s, %s) RETURNING id",
        (name, description, key, file.filename),
    )
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create test record")

    return {"id": row["id"], "name": name, "description": description}

@app.get("/api/lexi/robot/tests/{test_id}")
def get_test(test_id: str) -> dict:
    """Return metadata and testcases for a stored test."""
    row = db.fetchone(
        "SELECT id, name, description, filename, minio_key, created_at, variables "
        "FROM tests WHERE id = %s",
        (test_id,),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Test group not found")

    try:
        bytes_content = minio_client.get_object_to_bytes(row["minio_key"])
        cases = robot_parser.extract_testcases_from_robot_text(
            bytes_content.decode("utf-8")
        )
    except (OSError, UnicodeDecodeError, ValueError, TypeError):
        cases = []

    created_at = row.get("created_at")
    if hasattr(created_at, "isoformat"):
        created_at = created_at.isoformat()

    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "filename": row["filename"],
        "created_at": created_at,
        "testcases": cases,
        "variables": row.get("variables"),
    }

@app.delete("/api/lexi/robot/tests/{test_id}")
def delete_test(test_id: str) -> dict:
    """Delete a test record and remove its file from MinIO (best-effort)."""
    row = db.fetchone("SELECT id, minio_key FROM tests WHERE id = %s", (test_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Test not found")

    try:
        minio_client.remove_object(row["minio_key"])
    except OSError:
        # ignore MinIO deletion errors
        pass

    db.execute("DELETE FROM tests WHERE id = %s", (test_id,))
    return {"status": "deleted"}

@app.get("/api/lexi/robot/tests/{test_id}/cases")
def list_cases(test_id: str) -> dict:
    """Return test case names extracted from the stored .robot file."""
    row = db.fetchone("SELECT minio_key FROM tests WHERE id = %s", (test_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Test not found")

    try:
        content = minio_client.get_object_to_bytes(row["minio_key"]).decode("utf-8")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"MinIO error: {exc}") from exc

    cases = robot_parser.extract_testcases_from_robot_text(content)
    return {"testcases": cases}

@app.get("/api/lexi/robot/tests/{test_id}/schema")
def get_test_schema(test_id: str) -> dict:
    """
    Returns declared variables, per-test usage, and a simple JSON Schema
    used by the UI to render inputs and perform client-side validation.
    """
    row = db.fetchone("SELECT id, variables FROM tests WHERE id = %s", (test_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Test not found")

    vars_payload = row.get("variables") or {}
    declared = vars_payload.get("declared", []) if isinstance(vars_payload, dict) else []
    usage = vars_payload.get("usage", {}) if isinstance(vars_payload, dict) else {}

    properties = {}
    required = []
    for v in declared:
        name = v.get("name")
        if not name:
            continue
        default = v.get("default")
        prop = {"type": "string"}
        if default is not None:
            prop["default"] = default
        properties[name] = prop
        if default is None:
            required.append(name)

    json_schema = {"type": "object", "properties": properties}
    if required:
        json_schema["required"] = required

    return {"declared": declared, "usage": usage, "json_schema": json_schema}

@app.get("/api/lexi/robot/runs")
def list_all_runs(
    status: Optional[str] = Query(None),
    since: Optional[str] = Query(None),
    tags: Optional[str] = Query(None),
):
    """
    List all runs for all tests, with optional filtering by status, creation date, and tags.
    """
    # Base query
    query = """
        SELECT r.id AS run_id, r.test_id, t.name AS test_name,
               r.run_name, r.status, r.started_at, r.finished_at,
               r.tags, r.summary
        FROM runs r
        JOIN tests t ON t.id = r.test_id
        WHERE 1=1
    """
    params = []

    if status:
        query += " AND r.status = %s"
        params.append(status)

    if since:
        query += " AND r.created_at >= %s"
        params.append(since)

    if tags:
        # simple JSONB text match
        query += " AND r.tags::text ILIKE %s"
        params.append(f"%{tags}%")

    query += " ORDER BY r.created_at DESC"

    runs = db.fetchall(query, tuple(params))

    # Fetch test results for each run
    for run in runs:
        results = db.fetchall(
            "SELECT case_name, status, message, duration_ms FROM test_results WHERE run_id = %s",
            (run["run_id"],),
        )
        run["results"] = results

    return runs

@app.get("/api/lexi/robot/tests/{test_id}/runs")
def list_runs(
    test_id: str,
    status: Optional[str] = Query(None),
    since: Optional[str] = Query(None),
    tags: Optional[str] = Query(None),
) -> list:
    """List runs for a test with optional filters."""
    q = "SELECT id, run_name, tags, status, started_at, finished_at FROM runs WHERE test_id = %s"
    params = [test_id]

    if status:
        q += " AND status = %s"
        params.append(status)
    if since:
        q += " AND created_at >= %s"
        params.append(since)
    if tags:
        q += " AND tags::text ILIKE %s"
        params.append(f"%{tags}%")

    q += " ORDER BY created_at DESC"
    rows = db.fetchall(q, tuple(params))
    for r in rows:
        _serialize_row_timestamps(r)
    return rows

@app.post("/api/lexi/robot/tests/{test_id}/run")
def run_test(test_id: str, payload: schemas.RunCreateRequest, background_tasks: BackgroundTasks):
    """Run the full test case."""
    # Fetch test metadata
    test_row = db.fetchone(
        "SELECT id, minio_key, filename, variables FROM tests WHERE id = %s", (test_id,))
    if not test_row:
        raise HTTPException(status_code=404, detail="Test not found")

    # Proceed to schedule test
    run_id = db.fetchone(
        "INSERT INTO runs (test_id, run_name, tags, status, variables, cases) " \
        "VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
        (test_id, payload.run_name, json.dumps(payload.tags or []),
         "queued", json.dumps(payload.variables or {}), json.dumps(payload.cases))
    )["id"]

    # Fetch robot content and schedule background execution
    content_bytes = minio_client.get_object_to_bytes(test_row["minio_key"])
    background_tasks.add_task(
        robot_runner.run_tests_background, run_id,
        content_bytes, test_row["filename"], payload.variables, payload.cases
    )

    return {"run_id": run_id}

@app.get("/api/lexi/robot/tests/{test_id}/schema/{case_name}/required")
def get_test_case_required_schema(test_id: str, case_name: str):
    """
    Return required variables for a single testcase derived from declared + usage,
    filtered to include only variables whose reason originates from the test_case
    itself or from visited keywords.

    Response format:
      {
        "test_id": "<test_id>",
        "case_name": "<case_name>",
        "required_variables": [
          { "name","datatype","default","reason" }, ...
        ]
      }
    """
    # fetch test record
    row = db.fetchone("SELECT id, minio_key FROM tests WHERE id = %s", (test_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Test not found")

    try:
        content_bytes = minio_client.get_object_to_bytes(row["minio_key"])
    except Exception as exc:
        # MinIO error - surface as 500 so UI knows it's a backend/storage problem
        raise HTTPException(status_code=500, detail=f"MinIO error: {exc}") from exc

    try:
        content = content_bytes.decode("utf-8", errors="ignore")
    except UnicodeDecodeError:
        content = content_bytes.decode("latin-1", errors="ignore")

    result = robot_schema.get_required_variables_for_case(content, case_name, test_id)
    return result

@app.post("/api/lexi/robot/tests/{test_id}/queue")
def queue_test(test_id: str, payload: schemas.RunCreateRequest) -> dict:
    """
    Queue a run (persist variables and cases) but do not start execution.
    This stores run with status='queued' for later execution.
    """
    row = db.fetchone(
        "SELECT id, minio_key, filename, variables FROM tests WHERE id = %s", (test_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Test not found")

    uploaded_vars_payload = row.get("variables") or {}
    usage = uploaded_vars_payload.get(
        "usage", {}) if isinstance(uploaded_vars_payload, dict) else {}

    if payload.cases:
        known_cases = set(usage.keys())
        if known_cases:
            unknown = [c for c in payload.cases if c not in known_cases]
            if unknown:
                raise HTTPException(status_code=400, detail=f"Unknown testcase(s) {unknown}")

    run_row = db.insert_fetchone(
        "INSERT INTO runs (test_id, run_name, tags, status, variables, cases) "
        "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
        (
            test_id,
            payload.run_name,
            json.dumps(payload.tags or []),
            "queued",
            json.dumps(payload.variables or {}),
            json.dumps(payload.cases or []),
        ),
    )
    if not run_row:
        raise HTTPException(status_code=500, detail="Failed to create queued run")

    return {"run_id": run_row["id"], "status": "queued"}

@app.post("/api/lexi/robot/runs/{run_id}/queuestart")
def start_queued_run(run_id: str, background_tasks: BackgroundTasks) -> dict:
    """
    Start a queued run: fetches the stored run row, verifies state,
    loads the .robot file from MinIO and schedules the runner.
    """
    run_row = db.fetchone("SELECT id, test_id, run_name, tags, status, variables, cases "
                          "FROM runs WHERE id = %s", (run_id,))
    if not run_row:
        raise HTTPException(status_code=404, detail="Run not found")

    if run_row.get("status") != "queued":
        raise HTTPException(
            status_code=400, detail=f"Run is not queued (current status: {run_row.get('status')})")

    test_row = db.fetchone(
        "SELECT id, minio_key, filename FROM tests WHERE id = %s", (run_row["test_id"],))
    if not test_row:
        raise HTTPException(status_code=500, detail="Associated test record not found")

    try:
        file_bytes = minio_client.get_object_to_bytes(test_row["minio_key"])
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"MinIO error: {exc}") from exc

    variables = run_row.get("variables") or {}
    if isinstance(variables, str):
        variables = json.loads(variables)

    cases = run_row.get("cases") or []
    if isinstance(cases, str):
        cases = json.loads(cases)

    background_tasks.add_task(
        robot_runner.run_tests_background,
        run_id, file_bytes, test_row["filename"], variables, cases)

    return {"run_id": run_id, "message": "Run scheduled"}


@app.get("/api/lexi/robot/runs/list/queued")
def list_queued_runs(limit: int = 100) -> list:
    """Return a list of queued runs (most recent first)."""
    rows = db.fetchall(
        "SELECT id, test_id, run_name, tags, status, created_at FROM runs "
        "WHERE status = 'queued' ORDER BY created_at DESC LIMIT %s",
        (limit,),
    )
    for r in rows:
        _serialize_row_timestamps(r)
    return rows

@app.get("/api/lexi/robot/runs/logs/{run_id}")
def get_run(run_id: str) -> dict:
    """Return run metadata and per-test results for a run id."""
    row = db.fetchone(
        "SELECT id, test_id, run_name, tags, status, started_at, finished_at, summary "
        "FROM runs WHERE id = %s",
        (run_id,),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Run not found")

    _serialize_row_timestamps(row)
    results = db.fetchall(
        "SELECT case_name, status, message, duration_ms FROM test_results WHERE run_id = %s", 
        (run_id,))
    return {**row, "results": results}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
