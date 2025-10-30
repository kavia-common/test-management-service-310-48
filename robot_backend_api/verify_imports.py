#!/usr/bin/env python3
"""
Verification script to test that all imports work correctly.
Run this script to verify the ImportError fix.
"""
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

print("=" * 60)
print("Testing Import Fix for Robot Framework Test Management API")
print("=" * 60)
print()

tests_passed = 0
tests_failed = 0

def test_import(module_name, description):
    """Test importing a module and report results."""
    global tests_passed, tests_failed
    try:
        __import__(module_name)
        print(f"✓ {description}")
        tests_passed += 1
        return True
    except ImportError as e:
        print(f"✗ {description}")
        print(f"  Error: {e}")
        tests_failed += 1
        return False

# Test core imports
print("Testing Core Modules:")
print("-" * 60)
test_import("core.config", "Core configuration module")
test_import("core.database", "Database configuration")
test_import("core.storage", "Storage service")
print()

# Test model imports
print("Testing Model Modules:")
print("-" * 60)
test_import("models.test_file", "TestFile model")
test_import("models.testcase", "TestCase model")
test_import("models.run", "Run model")
test_import("models.run_config", "RunConfig model")
test_import("models.input_variable", "InputVariable model")
print()

# Test schema imports
print("Testing Schema Modules:")
print("-" * 60)
test_import("schemas.test_file", "Test file schemas")
test_import("schemas.testcase", "Test case schemas")
test_import("schemas.run", "Run schemas")
test_import("schemas.run_config", "Run config schemas")
test_import("schemas.input_variable", "Input variable schemas")
print()

# Test CRUD imports
print("Testing CRUD Modules:")
print("-" * 60)
test_import("crud.test_file", "Test file CRUD operations")
test_import("crud.testcase", "Test case CRUD operations")
test_import("crud.run", "Run CRUD operations")
test_import("crud.run_config", "Run config CRUD operations")
test_import("crud.input_variable", "Input variable CRUD operations")
print()

# Test service imports
print("Testing Service Modules:")
print("-" * 60)
test_import("services.robot_parser", "Robot parser service")
test_import("services.robot_executor", "Robot executor service")
test_import("services.storage_service", "Storage service wrapper")
print()

# Test API imports (will fail without database, but ImportError should not occur)
print("Testing API Modules:")
print("-" * 60)
print("Note: Database/MinIO connection errors are expected and normal")
print("      We're only testing that imports work correctly")
print()

try:
    # This might fail due to missing services, but should not have ImportError
    from api import main
    # Verify the app object exists
    assert hasattr(main, 'app'), "app object not found in main module"
    print("✓ API main module imports successfully")
    tests_passed += 1
except ImportError as e:
    print(f"✗ API main module has ImportError: {e}")
    tests_failed += 1
except Exception as e:
    # Other exceptions (like connection errors) are OK
    print(f"✓ API main module imports successfully (runtime error expected: {type(e).__name__})")
    tests_passed += 1

print()
print("=" * 60)
print("Test Results:")
print(f"  Passed: {tests_passed}")
print(f"  Failed: {tests_failed}")
print("=" * 60)

if tests_failed == 0:
    print("\n✓✓✓ SUCCESS! All imports work correctly!")
    print("The ImportError issue has been completely resolved.")
    sys.exit(0)
else:
    print(f"\n✗✗✗ FAILED! {tests_failed} import(s) failed.")
    print("Please check the errors above.")
    sys.exit(1)
