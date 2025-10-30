"""
Main FastAPI application for Robot Framework Test Management API.

This API provides comprehensive management and execution of Robot Framework tests,
including file upload, testcase extraction, execution with configuration, and
artifact retrieval.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from core.config import settings
from core.database import init_db
from api.routes import tests, testcases, runs, run_configs, inputs

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for application startup and shutdown.
    Initializes database on startup.
    """
    # Startup
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")


# Create FastAPI application with metadata
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    Robot Framework Test Management API
    
    This API provides comprehensive functionality for managing and executing Robot Framework tests:
    
    * **Test Files**: Upload, manage, and organize .robot test files
    * **Test Cases**: Extract and view individual test cases from robot files
    * **Test Runs**: Execute full files or specific test cases with real-time status tracking
    * **Run Configurations**: Create reusable execution configurations with variables and tags
    * **Input Variables**: View and manage variables extracted from test files
    * **Logs & Artifacts**: Access execution logs, output.xml, and report.html files
    
    ## Features
    
    - Parse .robot files to automatically extract testcases and variables
    - Execute tests with configurable timeout, tags, and variables
    - Store test files and execution artifacts in MinIO object storage
    - Track execution metadata in PostgreSQL database
    - Support batch/group execution with run configurations
    - Provide presigned URLs for secure artifact access
    - Background task execution for long-running tests
    
    ## WebSocket Support
    
    Currently, this API does not provide WebSocket endpoints for real-time updates.
    Test execution status can be polled via the GET /runs/{id} endpoint.
    """,
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "Test Files",
            "description": "Operations for managing robot test files"
        },
        {
            "name": "Test Cases",
            "description": "Operations for viewing extracted testcases"
        },
        {
            "name": "Test Runs",
            "description": "Operations for executing tests and retrieving results"
        },
        {
            "name": "Run Configurations",
            "description": "Operations for managing reusable execution configurations"
        },
        {
            "name": "Input Variables",
            "description": "Operations for viewing extracted input variables"
        }
    ]
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(tests.router)
app.include_router(testcases.router)
app.include_router(runs.router)
app.include_router(run_configs.router)
app.include_router(inputs.router)


# PUBLIC_INTERFACE
@app.get("/", tags=["Health"])
def health_check():
    """
    Health check endpoint.
    
    Returns basic health status of the API.
    
    Returns:
        dict: Health status message and version
    """
    return {
        "message": "Robot Framework Test Management API is running",
        "version": settings.app_version,
        "status": "healthy"
    }


# PUBLIC_INTERFACE
@app.get("/docs-usage", tags=["Documentation"])
def api_usage_guide():
    """
    API usage guide and examples.
    
    Provides helpful information about using the API effectively.
    
    Returns:
        dict: Usage guide and examples
    """
    return {
        "message": "Robot Framework Test Management API Usage Guide",
        "quick_start": {
            "1": "Upload a robot test file via POST /tests",
            "2": "View extracted testcases via GET /tests/{id}/testcases",
            "3": "Create a run configuration via POST /run-configs (optional)",
            "4": "Execute a test via POST /runs or POST /runs/testcase",
            "5": "Check execution status via GET /runs/{id}",
            "6": "Retrieve logs and artifacts via GET /runs/{id}/logs"
        },
        "execution_modes": {
            "full_file": "Execute all tests in a file via POST /runs",
            "specific_testcase": "Execute a single testcase via POST /runs/testcase",
            "batch_execution": "Execute multiple files/testcases via POST /runs/queue/execute"
        },
        "note": "All test executions run in the background. Poll the run status endpoint to check progress."
    }
