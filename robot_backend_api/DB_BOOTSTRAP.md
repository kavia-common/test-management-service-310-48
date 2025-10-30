# Database Bootstrap Implementation

## Overview

This document describes the automatic database table creation feature implemented in the Robot Framework Test Management API.

## Implementation Details

### Location
- **File**: `src/core/database.py`
- **Function**: `init_db()`
- **Startup**: Called from `src/api/main.py` lifespan event

### How It Works

1. **Startup Event**: When the FastAPI application starts, the `lifespan` context manager in `main.py` calls `init_db()`

2. **Model Import**: The `init_db()` function imports all model modules to ensure they are registered with SQLAlchemy's `Base.metadata`:
   - `models.test_file` (TestFile)
   - `models.testcase` (TestCase)
   - `models.run` (Run)
   - `models.run_config` (RunConfig)
   - `models.input_variable` (InputVariable)

3. **Table Creation**: After models are imported, `Base.metadata.create_all(bind=engine)` is called, which:
   - Creates all tables that don't already exist
   - Is idempotent (safe to call multiple times)
   - Skips tables that already exist

4. **Error Handling**: If the database is unreachable or any error occurs:
   - The error is logged with details
   - A warning is logged indicating the app will continue
   - The application starts anyway (doesn't crash)

### Tables Created

The following tables are automatically created:
1. `test_files` - Robot Framework test file metadata
2. `testcases` - Individual test cases extracted from files
3. `runs` - Test execution runs
4. `run_configs` - Reusable run configurations
5. `input_variables` - Variables extracted from test files

### Code Structure

```python
def init_db() -> None:
    """Initialize database by creating all tables."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Import all models to register them with Base.metadata
        logger.info("Importing all models...")
        from models import test_file, testcase, run, run_config, input_variable
        
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully (or already exist)")
        
    except Exception as e:
        # Log error but don't crash
        logger.error(f"Failed to initialize database: {e}")
        logger.warning("Application will continue but database operations may fail")
```

## Behavior

### Successful Initialization
When the database is available:
```
INFO:core.database:Importing all models...
INFO:core.database:Creating database tables...
INFO:core.database:Database tables created successfully (or already exist)
INFO:api.main:Database initialized successfully
```

### Database Unavailable
When the database is not available:
```
INFO:core.database:Importing all models...
INFO:core.database:Creating database tables...
ERROR:core.database:Failed to initialize database: (psycopg2.OperationalError) connection to server...
WARNING:core.database:Application will continue but database operations may fail
```

The application will still start and serve requests, but database operations will fail until the database becomes available.

## Testing

### Verify Model Registration
```bash
cd robot_backend_api
python3 -c "
import sys
sys.path.insert(0, 'src')
import os
os.environ['DATABASE_URL'] = 'postgresql://user:pass@localhost/testdb'
os.environ['MINIO_ENDPOINT'] = 'localhost:9000'
os.environ['MINIO_ACCESS_KEY'] = 'test'
os.environ['MINIO_SECRET_KEY'] = 'test'

from core.database import Base
from models import test_file, testcase, run, run_config, input_variable
print(f'Tables registered: {list(Base.metadata.tables.keys())}')
"
```

Expected output:
```
Tables registered: ['test_files', 'testcases', 'runs', 'run_configs', 'input_variables']
```

### Test Error Handling
```bash
# Run with an invalid DATABASE_URL to test error handling
export DATABASE_URL="postgresql://user:pass@localhost/testdb"
python3 run.py
# App should start with logged error but not crash
```

## Benefits

1. **Automatic Setup**: No need to run separate migration scripts on first deployment
2. **Idempotent**: Safe to run multiple times, existing tables are preserved
3. **Resilient**: Application starts even if database is temporarily unavailable
4. **Logging**: Clear logs indicate success or failure of initialization
5. **Developer-Friendly**: New developers can start the app without manual DB setup

## Integration with Deployment

This bootstrap approach works well with containerized deployments:
- Database container can start after the API container
- API will log errors but remain available
- Once database is ready, subsequent requests will work
- No need for init containers or startup probes for database

## Notes

- This is a simple bootstrap solution suitable for development and small deployments
- For production with complex migrations, consider using Alembic migrations
- The `Base.metadata.create_all()` only creates new tables, it doesn't modify existing ones
- Schema changes require proper migrations (not handled by this bootstrap)
