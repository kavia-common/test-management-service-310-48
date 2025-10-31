# Robot Backend API - Tests

This directory contains test scripts and diagnostic tools for the Robot Framework Test Management API.

## Test Files

### test_parser_variables.py

**Purpose:** Validates the robot parser's ability to extract variables from .robot files.

**Usage:**
```bash
python3 tests/test_parser_variables.py
```

**What it tests:**
- File-level variable extraction (from `*** Variables ***` section)
- Testcase-level variable extraction (assignments, set keywords, references)
- Variable detection in keyword arguments
- Variable detection in strings and expressions
- Proper handling of different variable types (${scalar}, @{list}, &{dict})

**Expected output:**
- Should detect 3 file-level variables
- Should detect 16+ testcase-level variables across 4 test cases
- Should show both assigned and referenced variables

### diagnose_endpoint.py

**Purpose:** Diagnostic tool for troubleshooting GET /inputs/{test_id}/{testcase_id} endpoint issues.

**Usage:**
```bash
# Diagnose specific endpoint
python3 tests/diagnose_endpoint.py <test_file_id> <testcase_id>

# Example: diagnose GET /inputs/2/4
python3 tests/diagnose_endpoint.py 2 4

# With defaults (test_id=2, testcase_id=4)
python3 tests/diagnose_endpoint.py
```

**Requirements:**
- Database must be running
- .env file must be configured with DATABASE_URL

**What it checks:**
1. Test file exists with specified ID
2. Testcase exists with specified ID
3. Testcase belongs to the correct test file
4. Variables exist with exact query parameters
5. Alternative queries to locate data
6. Variable counts for all testcases in the file

**Output:**
- Step-by-step validation results
- Alternative query results if main query returns empty
- Specific recommendations based on findings

## Running Tests

### Prerequisites

```bash
# Install dependencies
pip3 install -r requirements.txt

# For diagnose_endpoint.py, ensure database is running
# and .env is configured
```

### Run Parser Test

```bash
cd robot_backend_api
python3 tests/test_parser_variables.py
```

Expected: All tests pass, showing enhanced variable detection

### Run Endpoint Diagnostics

```bash
cd robot_backend_api
python3 tests/diagnose_endpoint.py 2 4
```

Expected: Detailed analysis of why endpoint returns empty or data exists

## Common Issues

### Parser Test Fails

**Issue:** Test fails with "Should have testcase-level variables"

**Possible causes:**
- Parser changes broke variable detection
- Robot Framework library not installed

**Fix:**
```bash
pip3 install robotframework
python3 tests/test_parser_variables.py
```

### Diagnostic Tool Fails

**Issue:** "connection to server ... failed: Connection refused"

**Cause:** Database not running

**Fix:**
```bash
# Start PostgreSQL
sudo systemctl start postgresql

# Or use Docker
docker-compose up -d postgres
```

**Issue:** "No module named 'core'"

**Cause:** Python path not set correctly

**Fix:**
```bash
# Run from robot_backend_api directory
cd robot_backend_api
python3 tests/diagnose_endpoint.py
```

## Interpreting Diagnostic Results

### Scenario 1: Variables found

```
✓ Test file exists: test.robot
✓ Testcase exists: My Test Case
Result: 5 variables
  Variables found:
    - ${username}: testuser
    - ${password}: testpass
    ...
```

**Meaning:** Endpoint should work correctly. If it returns empty, check route handler.

### Scenario 2: Variables exist but wrong test_file_id

```
⚠ No variables found - investigating...
Variables with testcase_id=4 (any test_file): 5
  - ${var1} (test_file_id=3, testcase_id=4)
```

**Meaning:** Data inconsistency. Variables were saved with wrong test_file_id.

**Fix:** Re-upload the robot file.

### Scenario 3: No variables for testcase

```
Variables with test_file_id=2 (all): 10
All testcases for test_file_id=2: 3
  - Testcase 1: Test A (3 variables)
  - Testcase 4: Test D (0 variables)
```

**Meaning:** Testcase 4 has no variables in the robot file, or parser didn't detect them.

**Fix:** Check robot file content, verify testcase has variable usage.

### Scenario 4: No variables at all

```
Variables with test_file_id=2 (all): 0
```

**Meaning:** Parser didn't extract any variables during upload.

**Fix:** Check parser logs, verify robot file has variables, re-upload.

## Creating New Tests

When adding new tests, follow this structure:

```python
#!/usr/bin/env python3
"""
Description of what this test does.
"""
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Set environment variables
os.environ['DATABASE_URL'] = 'postgresql://user:pass@localhost/testdb'
# ... other env vars ...

# Your test code here

if __name__ == "__main__":
    # Run test
    success = run_test()
    sys.exit(0 if success else 1)
```

## Integration with CI/CD

These tests can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run Parser Tests
  run: |
    cd robot_backend_api
    python3 tests/test_parser_variables.py

- name: Run Endpoint Diagnostics (if DB available)
  run: |
    cd robot_backend_api
    python3 tests/diagnose_endpoint.py
  if: env.DATABASE_URL != ''
```

## Support

For issues or questions about tests:
1. Check test output for specific error messages
2. Review ENDPOINT_FIX_SUMMARY.md for context
3. Enable debug logging: `export LOG_LEVEL=DEBUG`
4. Check application logs during test execution
