#!/usr/bin/env python3
"""
Test script to validate robot parser variable extraction.
This tests the enhanced parser with various variable patterns.
"""
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Set environment variables
os.environ['DATABASE_URL'] = 'postgresql://user:pass@localhost/testdb'
os.environ['MINIO_ENDPOINT'] = 'localhost:9000'
os.environ['MINIO_ACCESS_KEY'] = 'test'
os.environ['MINIO_SECRET_KEY'] = 'test'

from services.robot_parser import robot_parser
import tempfile


def test_variable_extraction():
    """Test various patterns of variable extraction."""
    
    # Create a comprehensive test robot file
    test_content = """*** Settings ***
Library    SeleniumLibrary
Library    RequestsLibrary

*** Variables ***
${BASE_URL}    http://example.com
${BROWSER}    chrome
@{USERS}    user1    user2    user3

*** Test Cases ***
Test Case With Variable Assignment
    [Documentation]    Test with various variable assignments
    [Tags]    smoke    regression
    ${username}=    Set Variable    testuser
    ${password}=    Set Variable    testpass
    ${result}=    Evaluate    1 + 1
    Set Test Variable    ${session_token}    abc123
    Set Suite Variable    ${suite_var}    suite_value
    Log    User: ${username}
    
Test Case With Keyword Arguments
    [Documentation]    Test with variables in keyword arguments
    Open Browser    ${BASE_URL}    ${BROWSER}
    Input Text    id=username    ${username}
    Input Text    id=password    ${password}
    Click Button    id=login
    ${element}=    Get WebElement    xpath=//div[@id='result']
    
Test Case With Variable References
    [Documentation]    Test with variable references
    ${api_url}=    Set Variable    ${BASE_URL}/api/v1
    ${response}=    GET    ${api_url}/users
    Should Be Equal    ${response.status_code}    200
    ${json}=    Set Variable    ${response.json()}
    
Test Case With Loop Variables
    [Documentation]    Test with loop constructs
    FOR    ${user}    IN    @{USERS}
        Log    Processing user: ${user}
        ${status}=    Check User Status    ${user}
        Should Be True    ${status}
    END
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.robot', delete=False) as f:
        f.write(test_content)
        temp_file = f.name

    try:
        print("=" * 80)
        print("ENHANCED PARSER TEST - Variable Extraction")
        print("=" * 80)
        print()
        
        testcases, file_vars, testcase_vars = robot_parser.parse_file(temp_file)
        
        print("File-level variables: {}".format(len(file_vars)))
        for v in file_vars:
            print("  - {}: {}".format(v['name'], v.get('default_value', 'N/A')))
        
        print("\nTestcases: {}".format(len(testcases)))
        for tc in testcases:
            print("\n{}".format(tc['name']))
            print("  Description: {}".format(tc.get('description', 'N/A')))
            print("  Tags: {}".format(tc.get('tags', 'N/A')))
            
            if tc['name'] in testcase_vars:
                vars_list = testcase_vars[tc['name']]
                print("  Variables ({}):".format(len(vars_list)))
                for v in vars_list:
                    desc = v.get('description', 'N/A')
                    val = v.get('default_value', 'N/A')
                    print("    * {}: {} - {}".format(v['name'], val, desc))
            else:
                print("  No testcase-level variables found")
        
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        
        total_tc_vars = sum(len(v) for v in testcase_vars.values())
        print("Total file-level variables: {}".format(len(file_vars)))
        print("Total testcase-level variables: {}".format(total_tc_vars))
        print("Total testcases: {}".format(len(testcases)))
        
        # Validation
        assert len(file_vars) >= 3, "Should have at least 3 file-level variables"
        assert len(testcases) == 4, "Should have 4 testcases"
        assert total_tc_vars > 0, "Should have testcase-level variables"
        
        print("\nAll tests passed!")
        return True
        
    except Exception as e:
        print("\nTest failed: {}".format(e))
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        os.unlink(temp_file)


if __name__ == "__main__":
    success = test_variable_extraction()
    sys.exit(0 if success else 1)
