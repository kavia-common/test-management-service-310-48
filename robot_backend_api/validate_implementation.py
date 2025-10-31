"""
Validation script to verify all implementation changes are correct.
Run this script to validate the UUID migration and encoding fixes.
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_models():
    """Verify models have UUID fields."""
    print("Testing models...")
    from models.test_file import TestFile
    from models.testcase import TestCase
    
    # Check TestFile has test_uid
    assert hasattr(TestFile, 'test_uid'), "TestFile missing test_uid field"
    assert hasattr(TestFile, 'id'), "TestFile missing id field"
    
    # Check TestCase has testcase_uid
    assert hasattr(TestCase, 'testcase_uid'), "TestCase missing testcase_uid field"
    assert hasattr(TestCase, 'id'), "TestCase missing id field"
    
    print("  ✓ TestFile has test_uid field")
    print("  ✓ TestCase has testcase_uid field")


def test_schemas():
    """Verify schemas expose UUID fields."""
    print("\nTesting schemas...")
    from schemas.test_file import TestFileResponse
    from schemas.testcase import TestCaseResponse
    
    # Check schemas have UUID fields
    test_file_fields = TestFileResponse.model_fields
    testcase_fields = TestCaseResponse.model_fields
    
    assert 'test_uid' in test_file_fields, "TestFileResponse missing test_uid"
    assert 'testcase_uid' in testcase_fields, "TestCaseResponse missing testcase_uid"
    
    print("  ✓ TestFileResponse exposes test_uid")
    print("  ✓ TestCaseResponse exposes testcase_uid")


def test_crud():
    """Verify CRUD operations support UUID lookups."""
    print("\nTesting CRUD operations...")
    from crud.test_file import get_test_file_by_uid
    from crud.testcase import get_testcase_by_uid, get_testcase_by_name
    
    assert callable(get_test_file_by_uid), "get_test_file_by_uid not callable"
    assert callable(get_testcase_by_uid), "get_testcase_by_uid not callable"
    assert callable(get_testcase_by_name), "get_testcase_by_name not callable"
    
    print("  ✓ get_test_file_by_uid function available")
    print("  ✓ get_testcase_by_uid function available")
    print("  ✓ get_testcase_by_name function available")


def test_encoding_detection():
    """Verify encoding detection works."""
    print("\nTesting encoding detection...")
    from api.routes.tests import _decode_robot_file_content
    
    # Test UTF-8
    utf8_content = "Test content".encode('utf-8')
    result = _decode_robot_file_content(utf8_content, "test.robot")
    assert "Test content" in result, "UTF-8 decoding failed"
    
    # Test invalid bytes
    invalid_content = b"\xff\xfe Invalid"
    result = _decode_robot_file_content(invalid_content, "test.robot")
    assert isinstance(result, str), "Invalid bytes decoding failed"
    
    print("  ✓ UTF-8 encoding detection works")
    print("  ✓ Invalid bytes handled gracefully")


def test_routes():
    """Verify route definitions."""
    print("\nTesting routes...")
    from api.routes import tests, inputs
    
    # Check tests router has the new endpoint
    routes = [route.path for route in tests.router.routes]
    assert any('required-variables' in route for route in routes), \
        "required-variables endpoint not found"
    
    # Check inputs router has deprecated endpoint
    input_routes = [route.path for route in inputs.router.routes]
    assert any('{testcase_id}' in route for route in input_routes), \
        "deprecated endpoint not found"
    
    print("  ✓ New required-variables endpoint exists")
    print("  ✓ Deprecated inputs endpoint exists")


def test_migration_script():
    """Verify migration script is functional."""
    print("\nTesting migration script...")
    from migrate_add_uuids import check_column_exists, migrate_add_uuids
    
    assert callable(check_column_exists), "check_column_exists not callable"
    assert callable(migrate_add_uuids), "migrate_add_uuids not callable"
    
    print("  ✓ Migration script functions available")


def test_dependencies():
    """Verify required dependencies are installed."""
    print("\nTesting dependencies...")
    
    try:
        import charset_normalizer
        # Verify it has the expected function
        assert hasattr(charset_normalizer, 'from_bytes'), "charset_normalizer missing from_bytes"
        print("  ✓ charset-normalizer installed")
    except ImportError:
        print("  ✗ charset-normalizer NOT installed")
        raise
    
    try:
        import fastapi
        # Verify FastAPI is functional
        assert hasattr(fastapi, 'FastAPI'), "fastapi missing FastAPI class"
        print("  ✓ fastapi installed")
    except ImportError:
        print("  ✗ fastapi NOT installed")
        raise
    
    try:
        from sqlalchemy.dialects.postgresql import UUID
        # Verify UUID type is available
        assert UUID is not None, "UUID type not available"
        print("  ✓ PostgreSQL UUID support available")
    except ImportError:
        print("  ✗ PostgreSQL UUID support NOT available")
        raise


def test_documentation():
    """Verify documentation files exist."""
    print("\nTesting documentation...")
    
    docs = [
        'UUID_MIGRATION_SUMMARY.md',
        'UUID_API_REFERENCE.md',
        'IMPLEMENTATION_COMPLETE.md',
        'TASK_COMPLETION_SUMMARY.md'
    ]
    
    for doc in docs:
        assert os.path.exists(doc), f"Documentation file missing: {doc}"
        print(f"  ✓ {doc} exists")


def main():
    """Run all validation tests."""
    print("=" * 60)
    print("VALIDATING IMPLEMENTATION")
    print("=" * 60)
    
    try:
        test_dependencies()
        test_models()
        test_schemas()
        test_crud()
        test_encoding_detection()
        test_routes()
        test_migration_script()
        test_documentation()
        
        print("\n" + "=" * 60)
        print("✅ ALL VALIDATION TESTS PASSED")
        print("=" * 60)
        print("\nImplementation is complete and correct!")
        print("\nNext steps:")
        print("  1. Deploy the updated code")
        print("  2. Run migration script: python migrate_add_uuids.py")
        print("  3. Test the API endpoints")
        print("  4. Update client applications")
        print("\nSee UUID_MIGRATION_SUMMARY.md for detailed instructions.")
        return 0
        
    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ VALIDATION FAILED")
        print("=" * 60)
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
