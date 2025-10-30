"""
Service for parsing Robot Framework test files to extract testcases and variables.
"""
from robot.parsing import get_model
from typing import List, Dict, Any, Tuple
import logging
import re

logger = logging.getLogger(__name__)


class RobotParser:
    """
    Parser for Robot Framework test files.
    Extracts testcases, variables, and metadata from .robot files.
    """

    def _normalize_var_name(self, name: str) -> str:
        """
        Normalize variable name to Robot-style scalar form if possible.

        Examples:
            "${USER}" -> "${USER}" (kept as-is for consistency)
            "@{LIST}" -> "@{LIST}"
            "&{DICT}" -> "&{DICT}"
        """
        if not name:
            return name
        name = name.strip()
        # Keep original token style (${...}, @{...}, &{...}) for DB storage as seen in current model usage.
        return name

    def _extract_file_level_variables(self, model) -> List[Dict[str, Any]]:
        """Extract variables from the Variables section."""
        variables: List[Dict[str, Any]] = []
        for section in model.sections:
            if section.header and hasattr(section.header, "data_tokens"):
                header_value = str(section.header.data_tokens[0].value).lower()
                if "variable" in header_value:
                    for item in getattr(section, "body", []):
                        if hasattr(item, "tokens") and len(item.tokens) > 0:
                            var_name = str(item.tokens[0].value).strip()
                            var_value = ""
                            var_desc = ""
                            if len(item.tokens) > 1:
                                var_value = str(item.tokens[1].value).strip()
                            if len(item.tokens) > 2:
                                for token in item.tokens[2:]:
                                    if hasattr(token, "type") and token.type == "COMMENT":
                                        var_desc = str(token.value).strip("#").strip()
                                        break
                            if var_name and (var_name.startswith("${") or var_name.startswith("@{") or var_name.startswith("&{")):
                                variables.append(
                                    {
                                        "name": self._normalize_var_name(var_name),
                                        "default_value": var_value,
                                        "description": var_desc,
                                    }
                                )
        return variables

    def _is_assignment_token(self, token_val: str) -> bool:
        """Return True if token looks like a variable assignment left-hand side like '${x}=' or '@{x}='."""
        if not token_val:
            return False
        s = token_val.strip()
        # Match patterns like ${X}=, @{L}=, &{D}=
        return bool(re.match(r"^(\$\{[^\}]+\}|\@\{[^\}]+\}|\&\{[^\}]+\})\s*=$", s))

    def _collect_tokens_text(self, node) -> List[str]:
        """Return list of non-empty textual values for tokens of a node, excluding pure whitespace."""
        toks: List[str] = []
        for t in getattr(node, "tokens", []) or []:
            try:
                # token.value may be attribute
                val = str(getattr(t, "value", "") or "")
                # Skip empty tokens and pure whitespace/separator tokens
                if val and val.strip():
                    toks.append(val)
            except Exception:
                pass
        return toks

    def _extract_testcase_level_variables(self, testcase_node) -> List[Dict[str, Any]]:
        """
        Extract variables used/assigned within a testcase body.

        Heuristics implemented:
          1) Detect assignment syntax in steps: '${var}=  Keyword ...' (first token like '${var}=')
          2) Detect Set Test Variable keyword calls: 'Set Test Variable  ${var}  value'
          3) Detect Set Suite Variable / Set Global Variable as well (treated as inputs; scope may be broader)
          4) Detect Return values assigned: same as (1) since Robot uses '${x}=  Keyword'
        """
        vars_found: Dict[str, Dict[str, Any]] = {}

        if not hasattr(testcase_node, "body"):
            return []

        for step in testcase_node.body:
            # Only look into keyword calls and similar executable rows
            if not hasattr(step, "type") or step.type != "KEYWORD":
                continue
                
            tokens_text = self._collect_tokens_text(step)
            if not tokens_text:
                continue

            # 1) Direct assignment like ${x}=
            first = tokens_text[0].strip()
            if self._is_assignment_token(first):
                # Extract ${x} from "${x}="
                var_name = first.rstrip("=").strip()
                # Try to capture default value if available
                default_val = None
                # The pattern is typically: ${var}=  Keyword  value...
                # So if there are more than 2 tokens, the third might be the value
                if len(tokens_text) > 2:
                    # Check if it's "Set Variable" keyword
                    if len(tokens_text) >= 2 and "set variable" in tokens_text[1].lower():
                        if len(tokens_text) > 2:
                            default_val = tokens_text[2].strip()
                
                vars_found[var_name] = {
                    "name": var_name,
                    "default_value": default_val,
                    "description": "Assigned from keyword return in testcase",
                }

            # 2) Keywords that set variables
            # Normalize keyword name (robot is case-insensitive)
            kw_lower = first.lower()
            setters = {"set test variable", "set suite variable", "set global variable"}
            if kw_lower in setters and len(tokens_text) >= 2:
                # format: Set Test Variable  ${var}  value...
                var_token = tokens_text[1].strip()
                if var_token.startswith("${") or var_token.startswith("@{") or var_token.startswith("&{"):
                    default_val = None
                    if len(tokens_text) >= 3:
                        # take the next arg as default if present
                        default_val = tokens_text[2].strip()
                    vars_found[var_token] = {
                        "name": var_token,
                        "default_value": default_val,
                        "description": f"Set via '{first}' keyword in testcase",
                    }

        return list(vars_found.values())

    # PUBLIC_INTERFACE
    def parse_file(self, file_path: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
        """
        Parse a robot test file and extract testcases and variables.

        Args:
            file_path: Path to the .robot file

        Returns:
            Tuple containing:
                - List of testcase dictionaries with name, description, and tags
                - List of file-level variable dictionaries with name, default_value, and description
                - Dict mapping testcase name -> list of testcase-level variable dictionaries

        Raises:
            Exception: If parsing fails
        """
        try:
            testcases: List[Dict[str, Any]] = []
            file_level_variables: List[Dict[str, Any]] = []
            testcase_level_variables: Dict[str, List[Dict[str, Any]]] = {}

            model = get_model(file_path)

            # File-level variables
            file_level_variables = self._extract_file_level_variables(model)

            # Test cases and their variables
            for section in model.sections:
                if section.header and hasattr(section.header, "data_tokens"):
                    header_value = str(section.header.data_tokens[0].value).lower()
                    if "test case" in header_value:
                        for item in getattr(section, "body", []):
                            if hasattr(item, "name"):
                                tc_name = str(item.name).strip()
                                tc_desc = ""
                                tc_tags: List[str] = []

                                if hasattr(item, "body"):
                                    for step in item.body:
                                        if hasattr(step, "type"):
                                            if step.type == "DOCUMENTATION":
                                                if hasattr(step, "tokens") and len(step.tokens) > 1:
                                                    tc_desc = str(step.tokens[1].value).strip()
                                            elif step.type == "TAGS":
                                                if hasattr(step, "tokens"):
                                                    tc_tags = [
                                                        str(t.value).strip()
                                                        for t in step.tokens[1:]
                                                        if hasattr(t, "value") and str(t.value).strip()
                                                    ]

                                # Collect testcase-scoped variables
                                tc_vars = self._extract_testcase_level_variables(item)
                                if tc_vars:
                                    testcase_level_variables[tc_name] = tc_vars

                                testcases.append(
                                    {
                                        "name": tc_name,
                                        "description": tc_desc,
                                        "tags": ",".join(tc_tags) if tc_tags else None,
                                    }
                                )

            logger.info(
                f"Parsed {len(testcases)} testcases, "
                f"{len(file_level_variables)} file-level vars, "
                f"{sum(len(v) for v in testcase_level_variables.values())} testcase-level vars from {file_path}"
            )
            return testcases, file_level_variables, testcase_level_variables

        except Exception as e:
            logger.error(f"Error parsing robot file {file_path}: {e}")
            raise

    # PUBLIC_INTERFACE
    def validate_robot_file(self, file_path: str) -> bool:
        """
        Validate if a file is a valid Robot Framework test file.

        Args:
            file_path: Path to the file

        Returns:
            bool: True if valid, False otherwise
        """
        try:
            get_model(file_path)
            return True
        except Exception as e:
            logger.error(f"Invalid robot file {file_path}: {e}")
            return False


# Global parser instance
robot_parser = RobotParser()
