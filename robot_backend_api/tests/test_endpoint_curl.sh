#!/bin/bash
# Test script for GET /inputs endpoint using curl
# This demonstrates how to test the endpoint once the API is running

set -e

API_BASE="http://localhost:8000"
TEST_FILE_ID="${1:-2}"
TESTCASE_ID="${2:-4}"

echo "=========================================="
echo "Testing GET /inputs Endpoints"
echo "=========================================="
echo ""
echo "API Base: $API_BASE"
echo "Test File ID: $TEST_FILE_ID"
echo "Testcase ID: $TESTCASE_ID"
echo ""

# Check if API is running
echo "Step 1: Checking if API is running..."
if curl -s -f "${API_BASE}/" > /dev/null 2>&1; then
    echo "✓ API is running"
else
    echo "✗ API is not running at $API_BASE"
    echo "  Start the API first: python3 run.py"
    exit 1
fi

echo ""
echo "Step 2: Testing GET /inputs/${TEST_FILE_ID} (file-level variables)"
echo "---"
response=$(curl -s "${API_BASE}/inputs/${TEST_FILE_ID}")
echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"

echo ""
echo "Step 3: Testing GET /inputs/${TEST_FILE_ID}/${TESTCASE_ID} (testcase-level variables)"
echo "---"
response=$(curl -s "${API_BASE}/inputs/${TEST_FILE_ID}/${TESTCASE_ID}")
echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"

# Check if response is empty array
if [ "$response" = "[]" ]; then
    echo ""
    echo "⚠ WARNING: Endpoint returned empty list"
    echo ""
    echo "Possible causes:"
    echo "  1. Testcase has no variables in the robot file"
    echo "  2. Data inconsistency (wrong test_file_id for variables)"
    echo "  3. Test file or testcase doesn't exist"
    echo ""
    echo "Run diagnostic tool:"
    echo "  python3 tests/diagnose_endpoint.py $TEST_FILE_ID $TESTCASE_ID"
else
    echo ""
    echo "✓ Endpoint returned data"
fi

echo ""
echo "=========================================="
echo "For more detailed diagnostics, run:"
echo "  python3 tests/diagnose_endpoint.py $TEST_FILE_ID $TESTCASE_ID"
echo "=========================================="
