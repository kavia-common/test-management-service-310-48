# Duplicate Storage Path Handling Fix

## Problem
The POST /tests endpoint was returning HTTP 500 errors when uploading files with duplicate storage paths due to `UniqueViolation` on the `test_files.storage_path` unique constraint.

## Root Cause
1. The initial implementation created test file records with temporary storage paths like `pending_{filename}`
2. When the same filename was uploaded multiple times, the temporary path would collide
3. No error handling existed for `IntegrityError` exceptions from duplicate storage paths
4. The database constraint violation would bubble up as an unhandled 500 error

## Solution Implemented

### 1. Enhanced CRUD Operations (`src/crud/test_file.py`)
- Added `get_test_file_by_storage_path()` to check for existing storage paths
- Added `create_test_file_safe()` that catches `IntegrityError` and returns `None` on duplicates
- This enables graceful handling of database constraint violations

### 2. Unique Path Generation (`src/services/storage_service.py`)
- Added `generate_unique_storage_path()` function
- Supports optional UUID suffix for guaranteed uniqueness
- Format: `robot_files/{test_file_id}/{filename}` or `robot_files/{test_file_id}/{stem}_{uuid}{ext}`

### 3. Robust Upload Flow (`src/api/routes/tests.py`)
The updated POST /tests endpoint now:

1. **Creates record with unique temporary path**: Uses UUID in temporary path to prevent initial collision
   ```python
   temp_storage_path = f"pending_{uuid.uuid4().hex[:12]}_{file.filename}"
   ```

2. **Retries on failure**: Attempts up to 3 times with different UUIDs if needed

3. **Checks for final path collision**: Before updating to final storage path, checks if it already exists

4. **Adds UUID suffix when needed**: If collision detected, generates unique filename with UUID

5. **Handles update failures**: Catches `IntegrityError` on storage_path update and retries with new UUID

6. **Cleanup on failure**: Removes database records and storage files if any step fails

## Behavior Changes

### Before Fix
- **Status**: HTTP 500 Internal Server Error
- **Error**: Unhandled `UniqueViolation` exception
- **User Experience**: Generic server error, no way to recover

### After Fix
- **Status**: HTTP 201 Created (always succeeds for valid files)
- **Behavior**: Automatically generates unique storage paths using UUID suffixes
- **User Experience**: Same file can be uploaded multiple times, each gets unique storage path
- **Storage Paths**: 
  - First upload: `robot_files/1/test.robot`
  - Second upload: `robot_files/2/test.robot` 
  - Collision case: `robot_files/3/test_a1b2c3d4.robot` (with UUID)

## Edge Cases Handled

1. **Concurrent uploads of same filename**: UUID in temporary path prevents race conditions
2. **Storage upload failure**: Database record is cleaned up
3. **Storage path update failure**: Both database and storage are cleaned up
4. **Multiple retry failures**: Returns 500 with clear error message after exhausting retries

## Testing Recommendations

1. Upload the same .robot file multiple times - should succeed each time
2. Upload files with identical names concurrently - should all succeed
3. Verify each upload gets a unique `storage_path` in the database
4. Verify all files are accessible in MinIO storage
5. Test the /tests GET endpoint returns all uploaded files

## Database Constraint
The `test_files.storage_path` unique constraint remains in place and continues to protect data integrity. The fix works with the constraint rather than removing it.

## Future Enhancements (Optional)

1. **Deduplication option**: Add a query parameter `?deduplicate=true` to return existing file instead of creating new one
2. **Conflict response**: Return HTTP 409 Conflict with existing resource location when duplicate is detected
3. **Content-based deduplication**: Hash file content and detect true duplicates vs. same filename
4. **Configurable behavior**: Allow users to choose between deduplication, unique naming, or conflict error
