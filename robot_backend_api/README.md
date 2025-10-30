# Robot Framework Test Management API

A FastAPI-based backend service for managing and executing Robot Framework tests with full CRUD operations, configuration management, and test execution capabilities.

## Features

- **Test File Management**: Upload, manage, and organize .robot test files
- **Test Case Extraction**: Automatically parse and extract test cases from robot files
- **Test Execution**: Execute full files or specific test cases with real-time status tracking
- **Run Configurations**: Create reusable execution configurations with variables and tags
- **Artifact Storage**: Store test files and execution artifacts in MinIO object storage
- **Database Tracking**: Track execution metadata in PostgreSQL database
- **Batch Execution**: Support for batch/group test executions
- **OpenAPI Documentation**: Comprehensive API documentation

## Prerequisites

- Python 3.8+
- PostgreSQL database
- MinIO object storage server

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file based on `.env.example`:
```bash
cp .env.example .env
```

3. Configure environment variables in `.env`:
   - `DATABASE_URL`: PostgreSQL connection string
   - `MINIO_ENDPOINT`: MinIO server endpoint
   - `MINIO_ACCESS_KEY`: MinIO access key
   - `MINIO_SECRET_KEY`: MinIO secret key

## Database Setup

### Automatic Table Creation

The application automatically creates all required database tables on startup using SQLAlchemy's `Base.metadata.create_all()`. This bootstrap process:

- **Runs automatically** when the application starts
- **Is idempotent** - safe to run multiple times (won't modify existing tables)
- **Handles errors gracefully** - app will start even if database is temporarily unavailable
- **Creates 5 tables**: `test_files`, `testcases`, `runs`, `run_configs`, `input_variables`

No manual database initialization is required. Simply ensure your PostgreSQL database exists and is accessible via the `DATABASE_URL` environment variable.

For more details, see [DB_BOOTSTRAP.md](DB_BOOTSTRAP.md).

### Manual Verification

To verify the database bootstrap implementation:
```bash
python3 verify_db_bootstrap.py
```

## Running the Application

### Option 1: Using the Python runner script (Recommended)
```bash
python3 run.py
```

### Option 2: Using the bash script
```bash
chmod +x run.sh
./run.sh
```

### Option 3: Using uvicorn directly
```bash
cd src
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

## API Documentation

Once the application is running, access the interactive API documentation at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Test Files
- `POST /tests` - Upload a robot test file
- `GET /tests` - List all test files
- `GET /tests/{id}` - Get test file details
- `PUT /tests/{id}` - Update test file metadata
- `DELETE /tests/{id}` - Delete a test file

### Test Cases
- `GET /tests/{id}/testcases` - Get test cases for a file

### Test Runs
- `POST /runs` - Execute a complete test file
- `POST /runs/testcase` - Execute a specific test case
- `GET /runs` - List all test runs
- `GET /runs/{id}` - Get run details
- `GET /runs/{id}/logs` - Get run logs and artifacts
- `POST /runs/queue/execute` - Queue batch execution

### Run Configurations
- `POST /run-configs` - Create run configuration
- `GET /run-configs` - List all configurations
- `GET /run-configs/{id}` - Get configuration details
- `PUT /run-configs/{id}` - Update configuration
- `DELETE /run-configs/{id}` - Delete configuration

### Input Variables
- `GET /inputs/{test_file_id}` - Get file-level variables
- `GET /inputs/{test_file_id}/{testcase_id}` - Get testcase-level variables

## Project Structure

```
robot_backend_api/
├── src/
│   ├── api/
│   │   ├── main.py              # FastAPI application entry point
│   │   └── routes/              # API route handlers
│   ├── core/
│   │   ├── config.py            # Configuration management
│   │   ├── database.py          # Database setup
│   │   └── storage.py           # MinIO storage service
│   ├── models/                  # SQLAlchemy database models
│   ├── schemas/                 # Pydantic request/response schemas
│   ├── crud/                    # CRUD operations
│   └── services/                # Business logic services
├── run.py                       # Python runner script
├── run.sh                       # Bash runner script
├── requirements.txt             # Python dependencies
└── .env.example                 # Environment variable template
```

## Development

### Code Quality
Run linting with flake8:
```bash
flake8 src/
```

### Testing
Run tests with pytest:
```bash
pytest
```

## Troubleshooting

### ImportError Issues
If you encounter import errors, ensure:
1. All `__init__.py` files are present in package directories
2. PYTHONPATH includes the `src` directory
3. Running from the correct directory

### Connection Errors
If you encounter connection errors:
1. Verify PostgreSQL is running and accessible
2. Verify MinIO server is running and accessible
3. Check environment variables in `.env` file
4. Ensure database and MinIO credentials are correct

## License

See LICENSE file for details.
