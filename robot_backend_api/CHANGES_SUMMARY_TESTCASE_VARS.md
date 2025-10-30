# Testcase-scoped Variable Extraction

Summary of changes to support parsing and persistence of testcase-level variables from .robot files.

What changed
- Updated services/robot_parser.py:
  - parse_file() now returns a 3-tuple: (testcases, file_level_variables, testcase_level_variables_map)
  - Implemented heuristics to detect testcase-scoped variables:
    - Left-hand side assignments like `${var}=  Keyword ...`
    - Set Test Variable / Set Suite Variable / Set Global Variable patterns
  - Continues to parse file-level variables from the Variables section

- Updated api/routes/tests.py upload flow:
  - Parses using the new 3-tuple
  - Creates the TestFile
  - Creates testcases, builds a name→id map
  - Persists file-level variables without testcase_id
  - Persists testcase-level variables with the associated testcase_id

Endpoints impact
- GET /inputs/{test_file_id}: unchanged — returns only file-level variables (testcase_id is NULL)
- GET /inputs/{test_file_id}/{testcase_id}: unchanged interface — now returns testcase-level variables stored with the testcase_id

Notes
- No changes to database schema were required
- No environment variables changed
- Parser uses safe heuristics and avoids marking mere usages as inputs to reduce noise
