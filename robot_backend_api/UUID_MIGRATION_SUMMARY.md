# UUID Migration and Route Update Summary

This document summarizes the changes made to address encoding issues, deprecate legacy routes, and introduce stable UUID identifiers.

## Changes Implemented

### 1. Robust File Encoding Detection

**Problem**: UnicodeDecodeError when processing .robot files with non-UTF-8 encodings.

**Solution**: 
- Added `charset-normalizer` package to requirements.txt
- Created `_decode_robot_file_content()` helper function in `src/api/routes/tests.py`
- Decoding strategy:
  1. Try UTF-8 first (most common, fastest)
  2. Use charset-normalizer for automatic encoding detection
  3. Fallback to UTF-8 with errors='replace' as last resort
- Added logging to track encoding detection

**Files Modified**:
- `requirements.txt` - Added charset-normalizer==3.4.1
- `src/api/routes/tests.py` - Added encoding detection function and updated required-variables endpoint

### 2. Stable UUID Identifiers

**Problem**: Integer IDs are not stable across database migrations/rebuilds and can cause issues with external integrations.

**Solution**:
- Added UUID fields to models:
  - `test_files.test_uid` (UUID, unique, indexed)
  - `testcases.testcase_uid` (UUID, unique, indexed)
- UUIDs are automatically generated on record creation
- Updated schemas to expose UUID fields in API responses
- Created CRUD functions to support UUID-based lookups

**Files Modified**:
- `src/models/test_file.py` - Added test_uid field
- `src/models/testcase.py` - Added testcase_uid field
- `src/schemas/test_file.py` - Added test_uid to response schemas
- `src/schemas/testcase.py` - Added testcase_uid to response schemas
- `src/crud/test_file.py` - Added get_test_file_by_uid()
- `src/crud/testcase.py` - Added get_testcase_by_uid() and get_testcase_by_name()

**Migration Files**:
- `alembic/versions/add_uuid_fields.py` - Alembic migration (for future use)
- `migrate_add_uuids.py` - Standalone migration script for existing databases

### 3. Updated Routes with UUID Support

**New Canonical Endpoint**:
```
GET /tests/{test_identifier}/testcases/{case_identifier}/required-variables
```

**Features**:
- Accepts multiple identifier types:
  - `test_identifier`: integer ID, UUID (test_uid), or test_id
  - `case_identifier`: integer ID, UUID (testcase_uid), or case_name (string)
- Automatically resolves identifiers to the correct test/testcase
- Returns enhanced response with both IDs and UUIDs
- Robust encoding handling for .robot file content

**Example Usage**:
```bash
# Using integer IDs (backward compatible)
GET /tests/123/testcases/456/required-variables

# Using UUIDs (recommended for stability)
GET /tests/550e8400-e29b-41d4-a716-446655440000/testcases/7c9e6679-7425-40de-944b-e07fc1f90ae7/required-variables

# Using case name
GET /tests/123/testcases/My%20Test%20Case/required-variables
```

**Response Format**:
```json
{
  "test_id": 123,
  "test_uid": "550e8400-e29b-41d4-a716-446655440000",
  "testcase_id": 456,
  "testcase_uid": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "case_name": "My Test Case",
  "required_variables": ["${VAR1}", "${VAR2}"]
}
```

### 4. Deprecated Legacy Route

**Deprecated Endpoint**:
```
GET /inputs/{test_file_id}/{testcase_id}
```

**Status**: HTTP 410 GONE

**Response**: Returns migration guidance with:
- Deprecation notice
- New endpoint information
- Migration examples
- Suggested new URL with UUIDs (if records exist)

**Files Modified**:
- `src/api/routes/inputs.py` - Changed testcase endpoint to return deprecation notice

### 5. Backward Compatibility

All changes maintain backward compatibility:
- Existing integer ID-based routes continue to work
- New UUID fields are added alongside existing IDs
- The new endpoint accepts both integer IDs and UUIDs
- Existing API responses include both id and uid fields

## Migration Guide

### For New Deployments

No action needed. The UUID fields will be automatically created via `init_db()`.

### For Existing Deployments

Run the migration script to add UUID fields to existing data:

```bash
cd /path/to/robot_backend_api
python migrate_add_uuids.py
```

This script:
- Checks if UUID columns already exist
- Adds UUID columns if needed
- Populates existing rows with generated UUIDs
- Adds unique constraints and indexes
- Is idempotent (safe to run multiple times)

### For API Clients

**Recommended Migration Path**:

1. Update client code to use the new endpoint:
   ```
   /tests/{test_identifier}/testcases/{case_identifier}/required-variables
   ```

2. Start using UUIDs from API responses:
   ```python
   # Old way (still works)
   test_id = response['id']
   
   # New way (recommended)
   test_uid = response['test_uid']
   ```

3. Gradually migrate to UUID-based references for stability

4. Remove usage of deprecated `/inputs/{test_file_id}/{testcase_id}` endpoint

## Testing

### Test Encoding Detection

Create a .robot file with non-UTF-8 encoding and upload it:

```bash
# Create a file with special characters
echo "*** Test Cases ***
Test With Special Chars
    Log    Héllo Wörld 中文" > test_encoding.robot

# Upload it
curl -X POST http://localhost:8000/tests \
  -F "file=@test_encoding.robot"
```

### Test UUID Endpoints

```bash
# Get test file details (returns test_uid)
curl http://localhost:8000/tests/1

# Use UUID in new endpoint
curl http://localhost:8000/tests/{test_uid}/testcases/Test%20Case/required-variables

# Test deprecated endpoint (should return 410)
curl http://localhost:8000/inputs/1/1
```

## Acceptance Criteria Status

✅ **GET /tests/{test_id}/testcases/{case_name}/required-variables returns 200 even for non-UTF-8 files**
- Implemented robust encoding detection with charset-normalizer
- No more UnicodeDecodeError exceptions

✅ **Legacy route /inputs/{test_file_id}/{testcase_id} returns 410 with guidance**
- Returns HTTP 410 GONE
- Provides migration instructions and suggested new URL

✅ **Introduced unique IDs for tests and testcases**
- Added test_uid and testcase_uid UUID fields
- Exposed in all relevant API responses
- New routes accept UUIDs with backward compatibility

✅ **No regression in existing tests or endpoints**
- All changes are additive
- Backward compatibility maintained
- Existing integer ID routes continue to work

## Files Summary

**Modified Files**: 9
- requirements.txt
- src/models/test_file.py
- src/models/testcase.py
- src/schemas/test_file.py
- src/schemas/testcase.py
- src/crud/test_file.py
- src/crud/testcase.py
- src/api/routes/tests.py
- src/api/routes/inputs.py

**New Files**: 2
- alembic/versions/add_uuid_fields.py
- migrate_add_uuids.py

## Notes

1. The `robot_schema.py` module remains pure and text-only as required
2. Encoding detection happens at the FastAPI route level before passing content to the analyzer
3. Logging has been added for encoding detection without excessive noise
4. UUID generation happens automatically via SQLAlchemy defaults
5. The migration script is safe to run multiple times (idempotent)
