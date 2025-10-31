"""
Test script to verify robust encoding detection for robot files.
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from api.routes.tests import _decode_robot_file_content


def test_utf8_encoding():
    """Test UTF-8 encoded content."""
    content = "*** Test Cases ***\nTest Case\n    Log    Hello World".encode('utf-8')
    result = _decode_robot_file_content(content, "test.robot")
    assert "Hello World" in result
    print("✓ UTF-8 encoding test passed")


def test_latin1_encoding():
    """Test Latin-1 encoded content with special characters."""
    content = "*** Test Cases ***\nTest Case\n    Log    Café".encode('latin-1')
    result = _decode_robot_file_content(content, "test.robot")
    assert "Caf" in result  # Should decode somehow
    print("✓ Latin-1 encoding test passed")


def test_mixed_encoding():
    """Test content with mixed/invalid encoding."""
    # Create bytes with invalid UTF-8 sequence
    content = b"*** Test Cases ***\nTest Case\n    Log    \xff\xfe Invalid"
    result = _decode_robot_file_content(content, "test.robot")
    assert "Test Cases" in result
    print("✓ Mixed encoding test passed")


def test_empty_content():
    """Test empty content."""
    content = b""
    result = _decode_robot_file_content(content, "empty.robot")
    assert result == ""
    print("✓ Empty content test passed")


if __name__ == "__main__":
    print("Testing encoding detection...")
    try:
        test_utf8_encoding()
        test_latin1_encoding()
        test_mixed_encoding()
        test_empty_content()
        print("\n✅ All encoding detection tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
