# UUID API Quick Reference

## Overview

This API now supports stable UUID identifiers alongside traditional integer IDs for better stability and external integrations.

## Key Changes

### 1. All Test Files and Test Cases Now Have UUIDs

**Test File Response**:
```json
{
  "id": 123,
  "test_uid": "550e8400-e29b-41d4-a716-446655440000",
  "name": "my_test.robot",
  "storage_path": "tests/123/my_test.robot",
  "created_at": "2025-01-15T12:00:00",
  "updated_at": "2025-01-15T12:00:00"
}
```

**Test Case Response**:
```json
{
  "id": 456,
  "testcase_uid": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "test_file_id": 123,
  "name": "My Test Case",
  "description": "Test description",
  "tags": "smoke,regression"
}
```

### 2. Flexible Identifier Support

The new required-variables endpoint accepts multiple identifier formats:

```
GET /tests/{test_identifier}/testcases/{case_identifier}/required-variables
```

**test_identifier** can be:
- Integer ID: `123`
- UUID: `550e8400-e29b-41d4-a716-446655440000`

**case_identifier** can be:
- Integer ID: `456`
- UUID: `7c9e6679-7425-40de-944b-e07fc1f90ae7`
- Case name: `My%20Test%20Case` (URL-encoded)

## API Examples

### Get Test File by ID

```bash
curl -X GET http://localhost:8000/tests/123
```

**Response**:
```json
{
  "id": 123,
  "test_uid": "550e8400-e29b-41d4-a716-446655440000",
  "name": "my_test.robot",
  "description": null,
  "storage_path": "tests/123/my_test.robot",
  "created_at": "2025-01-15T12:00:00.000Z",
  "updated_at": "2025-01-15T12:00:00.000Z",
  "testcase_count": 5
}
```

### Get Required Variables (Integer IDs)

```bash
curl -X GET "http://localhost:8000/tests/123/testcases/456/required-variables"
```

### Get Required Variables (UUIDs)

```bash
curl -X GET "http://localhost:8000/tests/550e8400-e29b-41d4-a716-446655440000/testcases/7c9e6679-7425-40de-944b-e07fc1f90ae7/required-variables"
```

### Get Required Variables (Case Name)

```bash
curl -X GET "http://localhost:8000/tests/123/testcases/My%20Test%20Case/required-variables"
```

**Response** (all methods):
```json
{
  "test_id": 123,
  "test_uid": "550e8400-e29b-41d4-a716-446655440000",
  "testcase_id": 456,
  "testcase_uid": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "case_name": "My Test Case",
  "required_variables": [
    "${USERNAME}",
    "${PASSWORD}",
    "${API_URL}"
  ]
}
```

## Python Client Example

```python
import requests
import json

# Upload a test file
with open('my_test.robot', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/tests',
        files={'file': f}
    )
test_data = response.json()

# Extract both ID and UUID
test_id = test_data['id']
test_uid = test_data['test_uid']

# Get testcases
response = requests.get(f'http://localhost:8000/tests/{test_id}/testcases')
testcases = response.json()['testcases']

# Get required variables using UUID (recommended for stability)
for tc in testcases:
    tc_uid = tc['testcase_uid']
    response = requests.get(
        f'http://localhost:8000/tests/{test_uid}/testcases/{tc_uid}/required-variables'
    )
    vars_data = response.json()
    print(f"Test Case: {vars_data['case_name']}")
    print(f"Required Variables: {vars_data['required_variables']}")
```

## JavaScript Client Example

```javascript
// Upload a test file
const formData = new FormData();
formData.append('file', fileInput.files[0]);

const uploadResponse = await fetch('http://localhost:8000/tests', {
  method: 'POST',
  body: formData
});
const testData = await uploadResponse.json();

// Store both ID and UUID
const testId = testData.id;
const testUid = testData.test_uid;

// Get testcases
const testcasesResponse = await fetch(`http://localhost:8000/tests/${testId}/testcases`);
const testcasesData = await testcasesResponse.json();

// Get required variables using UUID (recommended)
for (const tc of testcasesData.testcases) {
  const tcUid = tc.testcase_uid;
  const varsResponse = await fetch(
    `http://localhost:8000/tests/${testUid}/testcases/${tcUid}/required-variables`
  );
  const varsData = await varsResponse.json();
  console.log(`Test Case: ${varsData.case_name}`);
  console.log(`Required Variables:`, varsData.required_variables);
}
```

## Migration from Legacy Endpoints

### Old Endpoint (DEPRECATED)
```
GET /inputs/{test_file_id}/{testcase_id}
```
**Status**: HTTP 410 GONE

### New Endpoint
```
GET /tests/{test_identifier}/testcases/{case_identifier}/required-variables
```

### Migration Steps

1. Replace endpoint URL in your code
2. Update to use UUIDs for stability (optional but recommended)
3. Handle new response format (includes more metadata)

**Before**:
```python
# Old endpoint (deprecated)
response = requests.get(f'http://localhost:8000/inputs/{test_id}/{testcase_id}')
variables = response.json()  # Returns list of variable objects
```

**After**:
```python
# New endpoint (recommended)
response = requests.get(
    f'http://localhost:8000/tests/{test_uid}/testcases/{tc_uid}/required-variables'
)
data = response.json()
variables = data['required_variables']  # Returns list of variable names
test_uid = data['test_uid']  # Available for future use
testcase_uid = data['testcase_uid']  # Available for future use
```

## Best Practices

### 1. Use UUIDs for External References

When storing references in external systems, use UUIDs instead of integer IDs:

```python
# Good: Stable across database migrations
external_db.store('test_reference', test_uid)

# Avoid: May change after database rebuild
external_db.store('test_reference', test_id)
```

### 2. Cache UUID Mappings

If you need to frequently look up tests, cache the UUID mappings:

```python
test_cache = {}

def get_test_by_uid(uid):
    if uid not in test_cache:
        response = requests.get(f'http://localhost:8000/tests')
        for test in response.json():
            test_cache[test['test_uid']] = test
    return test_cache.get(uid)
```

### 3. Handle Both ID Types

For backward compatibility, support both integer IDs and UUIDs in your application:

```python
def get_required_variables(test_ref, case_ref):
    """
    Get required variables for a test case.
    
    Args:
        test_ref: Test file ID (int) or UUID (str)
        case_ref: Test case ID (int), UUID (str), or name (str)
    """
    response = requests.get(
        f'http://localhost:8000/tests/{test_ref}/testcases/{case_ref}/required-variables'
    )
    return response.json()
```

## Error Handling

### Invalid Identifier Format

```json
{
  "detail": "Invalid test_identifier: must be an integer ID or UUID"
}
```

### Test Not Found

```json
{
  "detail": "Test file with identifier 550e8400-e29b-41d4-a716-446655440000 not found"
}
```

### Test Case Not Belonging to Test File

```json
{
  "detail": "Test case does not belong to the specified test file"
}
```

### Encoding Issues (Now Fixed)

Previously, non-UTF-8 files would cause:
```json
{
  "detail": "Failed to retrieve test file content: 'utf-8' codec can't decode..."
}
```

Now, the API automatically detects and handles various encodings gracefully.

## Database Schema

### test_files Table

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key (auto-increment) |
| test_uid | UUID | Unique stable identifier |
| name | String | File name |
| description | Text | Optional description |
| storage_path | String | MinIO storage path |
| created_at | DateTime | Creation timestamp |
| updated_at | DateTime | Last update timestamp |

### testcases Table

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key (auto-increment) |
| testcase_uid | UUID | Unique stable identifier |
| test_file_id | Integer | Foreign key to test_files |
| name | String | Test case name |
| description | Text | Test case description |
| tags | Text | Comma-separated tags |

## Support

For issues or questions:
1. Check the OpenAPI documentation at `/docs`
2. Review the UUID_MIGRATION_SUMMARY.md
3. Check server logs for encoding detection messages
4. Verify your client handles both integer IDs and UUIDs
