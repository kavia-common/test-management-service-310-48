"""
A simple parser to extract test case names from a Robot Framework .robot file content.
It finds the first '*** Test Cases ***' section (case-insensitive) and collects
top-level lines (not indented) until the next section. This avoids using internal
Robot parser APIs.
"""

from typing import List


def extract_testcases_from_robot_text(content: str) -> List[str]:
    """
    Extract top-level test case names from a .robot file content.

    Args:
        content (str): The text content of a .robot file.

    Returns:
        List[str]: List of test case names.
    """
    lines = content.splitlines()
    start = None

    # Locate the first "*** Test Cases ***" section
    for i, line in enumerate(lines):
        if line.strip().lower().startswith("*** test cases ***"):
            start = i + 1
            break

    if start is None:
        return []

    cases: List[str] = []

    for line in lines[start:]:
        stripped = line.strip()

        # Stop at the next section
        if stripped.startswith("***"):
            break

        if not stripped:
            continue

        # Top-level lines without indentation are treated as test case names
        if line.lstrip() == line:
            cases.append(stripped)

    return cases
