"""
Robot Framework test schema analyzer.

Provides analysis of .robot files to extract required variables for test cases,
tracking variables assigned in visited keywords to avoid false positives.
"""
from robot.parsing import get_model
from typing import Dict, Set, Any, Optional
import logging
import re

logger = logging.getLogger(__name__)


def _normalize_var(name: str) -> str:
    """
    Normalize a variable name to a canonical form.
    
    Args:
        name: Variable name (e.g., "${VAR}", "@{LIST}", "&{DICT}")
        
    Returns:
        str: Normalized variable name
    """
    if not name:
        return name
    return name.strip()


def _extract_vars_from_text(text: str) -> Set[str]:
    """
    Extract variable references from text using regex.
    
    Args:
        text: Text to search for variables
        
    Returns:
        Set[str]: Set of variable names found
    """
    if not text:
        return set()
    # Match ${VAR}, @{LIST}, &{DICT}
    pattern = r'(\$\{[^\}]+\}|\@\{[^\}]+\}|\&\{[^\}]+\})'
    matches = re.findall(pattern, text)
    return set(_normalize_var(m) for m in matches)


def _is_assignment_token(token_val: str) -> bool:
    """
    Check if token represents a variable assignment.
    
    Args:
        token_val: Token value to check
        
    Returns:
        bool: True if it's an assignment token like "${x}="
    """
    if not token_val:
        return False
    s = token_val.strip()
    # Match patterns like ${X}=, @{L}=, &{D}=
    return bool(re.match(r'^(\$\{[^\}]+\}|\@\{[^\}]+\}|\&\{[^\}]+\})\s*=$', s))


def _assigned_vars(keyword_node) -> Set[str]:
    """
    Extract variables that are assigned within a keyword definition.
    
    This identifies variables that are set by the keyword, which should
    not be considered as required inputs. Also includes keyword arguments.
    
    Args:
        keyword_node: Keyword node from robot model
        
    Returns:
        Set[str]: Set of variable names assigned in this keyword
    """
    assigned: Set[str] = set()
    
    if not hasattr(keyword_node, 'body'):
        return assigned
    
    # Check for [Arguments] in keyword body
    for step in keyword_node.body:
        if not hasattr(step, 'tokens'):
            continue
            
        tokens = [str(getattr(t, 'value', '') or '') for t in step.tokens if hasattr(t, 'value')]
        if not tokens:
            continue
        
        first = tokens[0].strip()
        
        # Track [Arguments] as assigned variables
        if first.lower() == '[arguments]':
            for token in tokens[1:]:
                token_clean = token.strip()
                if token_clean and (token_clean.startswith('${') or token_clean.startswith('@{') or token_clean.startswith('&{')):
                    assigned.add(token_clean)
            continue
        
        # Check for assignment syntax: ${var}=  Keyword ...
        if _is_assignment_token(first):
            var_name = first.rstrip('=').strip()
            assigned.add(var_name)
        
        # Check for Set Variable keywords
        if len(tokens) >= 2:
            kw_lower = first.lower()
            if kw_lower in {'set test variable', 'set suite variable', 'set global variable'}:
                var_token = tokens[1].strip()
                if var_token.startswith('${') or var_token.startswith('@{') or var_token.startswith('&{'):
                    assigned.add(var_token)
    
    return assigned


def _extract_file_level_variables(model) -> Set[str]:
    """
    Extract variables defined in the Variables section.
    
    Args:
        model: Robot model from parsing
        
    Returns:
        Set[str]: Set of variable names defined at file level
    """
    file_vars: Set[str] = set()
    
    for section in model.sections:
        if not hasattr(section, 'header') or not section.header:
            continue
            
        header_tokens = getattr(section.header, 'data_tokens', [])
        if not header_tokens:
            continue
            
        header_val = str(header_tokens[0].value).lower()
        if 'variable' in header_val:
            for item in getattr(section, 'body', []):
                if hasattr(item, 'tokens') and len(item.tokens) > 0:
                    var_name = str(item.tokens[0].value).strip()
                    if var_name and (var_name.startswith('${') or var_name.startswith('@{') or var_name.startswith('&{')):
                        file_vars.add(var_name)
    
    return file_vars


def _build_keyword_map(model) -> Dict[str, Any]:
    """
    Build a map of keyword names to their definitions.
    
    Args:
        model: Robot model from parsing
        
    Returns:
        Dict[str, Any]: Map of keyword name to keyword node
    """
    kw_map: Dict[str, Any] = {}
    
    for section in model.sections:
        if not hasattr(section, 'header') or not section.header:
            continue
            
        header_tokens = getattr(section.header, 'data_tokens', [])
        if not header_tokens:
            continue
            
        header_val = str(header_tokens[0].value).lower()
        if 'keyword' in header_val:
            for item in getattr(section, 'body', []):
                if hasattr(item, 'name'):
                    kw_name = str(item.name).strip()
                    kw_map[kw_name.lower()] = item
    
    return kw_map


def _find_best_keyword_match(call_name: str, kw_map: Dict[str, Any]) -> Optional[str]:
    """
    Find the best matching keyword definition for a call.
    
    Prioritizes exact match, then startswith, then substring match.
    
    Args:
        call_name: Name of keyword being called
        kw_map: Map of available keyword definitions
        
    Returns:
        Optional[str]: Best matching keyword key, or None
    """
    call_lower = call_name.lower()
    
    # 1. Exact match (case-insensitive)
    if call_lower in kw_map:
        return call_lower
    
    # 2. Prefix match
    for key in kw_map.keys():
        if call_lower.startswith(key) or key.startswith(call_lower):
            return key
    
    # 3. Substring match
    for key in kw_map.keys():
        if call_lower in key or key in call_lower:
            return key
    
    return None


def _process_keywords(
    testcase_node,
    kw_map: Dict[str, Any],
    visited: Set[str],
    assigned_in_visited_keywords: Set[str]
) -> Set[str]:
    """
    Recursively process keywords in a testcase to extract used variables.
    
    Tracks variables assigned within visited keywords to avoid counting them
    as required inputs.
    
    Args:
        testcase_node: Test case or keyword node
        kw_map: Map of keyword definitions
        visited: Set of already visited keyword names (to prevent infinite recursion)
        assigned_in_visited_keywords: Set of variables assigned in visited keywords
        
    Returns:
        Set[str]: Set of variable names used
    """
    used_vars: Set[str] = set()
    
    if not hasattr(testcase_node, 'body'):
        return used_vars
    
    for step in testcase_node.body:
        if not hasattr(step, 'tokens'):
            continue
        
        tokens = [str(getattr(t, 'value', '') or '').strip() 
                  for t in step.tokens if hasattr(t, 'value') and str(getattr(t, 'value', '')).strip()]
        
        if not tokens:
            continue
        
        first = tokens[0]
        
        # Track assignments in this testcase/keyword
        if _is_assignment_token(first):
            var_name = first.rstrip('=').strip()
            assigned_in_visited_keywords.add(var_name)
        
        # Check for Set Variable keywords
        if len(tokens) >= 2:
            kw_lower = first.lower()
            if kw_lower in {'set test variable', 'set suite variable', 'set global variable'}:
                var_token = tokens[1].strip()
                if var_token.startswith('${') or var_token.startswith('@{') or var_token.startswith('&{'):
                    assigned_in_visited_keywords.add(var_token)
        
        # Extract variables from all tokens
        for token in tokens:
            used_vars.update(_extract_vars_from_text(token))
        
        # If first token is a keyword call, recurse into it
        # Skip if it's an assignment or a known built-in
        if not _is_assignment_token(first):
            cand = _find_best_keyword_match(first, kw_map)
            if cand and cand not in visited:
                # Before recursion, get variables assigned in this keyword
                kw_assigned = _assigned_vars(kw_map[cand])
                assigned_in_visited_keywords.update(kw_assigned)
                
                # Now recurse
                visited.add(cand)
                kw_vars = _process_keywords(kw_map[cand], kw_map, visited, assigned_in_visited_keywords)
                used_vars.update(kw_vars)
    
    return used_vars


def _cleanup_candidates(vars_set: Set[str], assigned_in_visited: Set[str], file_level_vars: Set[str]) -> Set[str]:
    """
    Remove built-in, system variables, file-level variables, and variables assigned in visited keywords.
    
    Args:
        vars_set: Set of candidate variable names
        assigned_in_visited: Set of variables assigned in visited keywords
        file_level_vars: Set of variables defined at file level
        
    Returns:
        Set[str]: Cleaned set of variable names
    """
    skip_vars = {
        '${curdir}', '${tempdir}', '${execdir}', '${/}', '${:}',
        '${space}', '${empty}', '${true}', '${false}', '${null}',
        '${test name}', '${test status}', '${suite name}', '${suite status}',
        '${prev test name}', '${prev test status}', '${test message}',
        '${test documentation}', '${test tags}', '${keyword status}',
        '${keyword message}', '${log level}', '${output dir}', '${output file}',
        '${log file}', '${report file}', '${debug file}', '${suite documentation}',
        '${suite metadata}', '${suite source}'
    }
    
    cleaned: Set[str] = set()
    for var in vars_set:
        var_lower = var.lower()
        # Skip built-in variables
        if var_lower in skip_vars:
            continue
        # Skip variables assigned in visited keywords
        if var in assigned_in_visited:
            continue
        # Skip file-level variables
        if var in file_level_vars:
            continue
        cleaned.add(var)
    
    return cleaned


# PUBLIC_INTERFACE
def get_required_variables_for_case(content: str, case_name: str, test_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Analyze a robot test file and extract required variables for a specific test case.
    
    This function parses the robot file, identifies the specified test case,
    traverses its keywords, and determines which variables are required inputs
    (excluding variables assigned within the test case or its keywords).
    
    Args:
        content: Robot file content as string
        case_name: Name of the test case to analyze
        test_id: Optional test file ID for reference
        
    Returns:
        Dict containing:
            - test_id: Test file ID (if provided)
            - case_name: Test case name
            - required_variables: List of required variable names
            
    Raises:
        ValueError: If test case not found or parsing fails
    """
    import tempfile
    import os
    
    logger.info(f"Analyzing required variables for test case: {case_name}")
    
    # Write content to temporary file for parsing
    with tempfile.NamedTemporaryFile(mode='w', suffix='.robot', delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        model = get_model(tmp_path)
        
        # Extract file-level variables
        file_level_vars = _extract_file_level_variables(model)
        
        # Build keyword map
        kw_map = _build_keyword_map(model)
        
        # Find the test case
        target_case = None
        for section in model.sections:
            if not hasattr(section, 'header') or not section.header:
                continue
            
            header_tokens = getattr(section.header, 'data_tokens', [])
            if not header_tokens:
                continue
            
            header_val = str(header_tokens[0].value).lower()
            if 'test case' in header_val:
                for item in getattr(section, 'body', []):
                    if hasattr(item, 'name') and str(item.name).strip() == case_name:
                        target_case = item
                        break
                if target_case:
                    break
        
        if not target_case:
            raise ValueError(f"Test case '{case_name}' not found in robot file")
        
        # Process keywords and extract variables
        visited: Set[str] = set()
        assigned_in_visited_keywords: Set[str] = set()
        used_vars = _process_keywords(target_case, kw_map, visited, assigned_in_visited_keywords)
        
        # Clean up the variable list
        required_vars = _cleanup_candidates(used_vars, assigned_in_visited_keywords, file_level_vars)
        
        logger.info(f"Found {len(required_vars)} required variables for '{case_name}'")
        
        result = {
            "case_name": case_name,
            "required_variables": sorted(list(required_vars))
        }
        
        if test_id is not None:
            result["test_id"] = test_id
        
        return result
        
    finally:
        # Clean up temp file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
