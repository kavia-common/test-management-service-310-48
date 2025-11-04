# app/robot_schema.py
"""
Robot .robot static analyzer — filtered, recursive.

This module provides:
 - get_case_inputs_for_content(content, case_name)   -> original analyzer output
 - get_required_variables_for_case(content, case_name, test_id) -> filtered response
"""

import re
from typing import List, Dict, Set, Tuple, Any

USAGE_RE = re.compile(r'\$\{([A-Za-z0-9_]+)\}')

def section_re(n: str) -> re.Pattern:
    """ Return regex pattern for section headers """
    return re.compile(r'^\s*\*\*\*\s*' + re.escape(n) + r'\s*\*\*', re.I)

CREATE_SESSION_RE = re.compile(r'create\s+session\s+([A-Za-z0-9_]+)\s+(.+)', re.I)
HTTP_ON_SESSION_RE = re.compile(
    r'(get|post|put|delete|patch)\s+on\s+session\s+([A-Za-z0-9_]+)\s+(.+)', re.I
)
GET_FULL_URL_RE = re.compile(r'^\s*(get|post|put|delete|patch)\s+(.+)', re.I)
ASSIGNMENT_RE = re.compile(r'^\s*(\$\{([A-Za-z0-9_]+)\})\s*=')
SET_SUITE_TEST_RE = re.compile(
    r'^\s*set\s+(?:suite|test)\s+variable\s+(\$\{[A-Za-z0-9_]+\})', re.I
)

# ------------------------- helpers -------------------------
def _lines(text: str) -> List[str]:
    return text.splitlines()

def _section_lines(content: str, header: str) -> List[str]:
    header_re = section_re(header)
    lines = _lines(content)
    start = None
    for i, ln in enumerate(lines):
        if header_re.match(ln):
            start = i + 1
            break
    if start is None:
        return []
    out: List[str] = []
    for ln in lines[start:]:
        if ln.strip().startswith('***'):
            break
        out.append(ln)
    return out

def _declared_vars(content: str) -> Dict[str, Dict]:
    """Return suite-level variables mapping: name -> {name, default}."""
    lines = _section_lines(content, "Variables")
    out: Dict[str, Dict] = {}
    for ln in lines:
        if not ln.strip():
            continue
        parts = re.split(r'\s{2,}|\t', ln.strip())
        if not parts:
            continue
        m = re.match(r'^\$\{([A-Za-z0-9_]+)\}$', parts[0])
        if not m:
            m2 = re.match(r'^\$\{([A-Za-z0-9_]+)\}', parts[0])
            if not m2:
                continue
            name = m2.group(1)
        else:
            name = m.group(1)
        default = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
        out[name] = {"name": name, "default": default}
    return out

def _find_test_block(content: str, case_name: str) -> List[str]:
    lines = _section_lines(content, "Test Cases")
    if not lines:
        return []
    target = case_name.strip().lower()
    cur = None
    block: List[str] = []
    collecting = False
    for ln in lines:
        if ln == ln.lstrip() and ln.strip():
            if cur and cur.strip().lower() == target:
                return block
            cur = ln.strip()
            block = [ln]
            collecting = True
        else:
            if collecting:
                block.append(ln)
    if cur and cur.strip().lower() == target:
        return block
    return []

def _parse_keywords(content: str) -> Dict[str, List[str]]:
    lines = _section_lines(content, "Keywords")
    kw: Dict[str, List[str]] = {}
    if not lines:
        return kw
    cur = None
    block: List[str] = []
    collecting = False
    for ln in lines:
        if ln == ln.lstrip() and ln.strip():
            if cur:
                kw[cur.strip().lower()] = block
            cur = ln.strip()
            block = [ln]
            collecting = True
        else:
            if collecting:
                block.append(ln)
    if cur:
        kw[cur.strip().lower()] = block
    return kw

def _sessions_map(content: str) -> Dict[str, str]:
    sm: Dict[str, str] = {}
    for ln in _lines(content):
        m = CREATE_SESSION_RE.search(ln)
        if m:
            sm[m.group(1)] = m.group(2).strip()
    return sm

def _assigned_vars(block: List[str]) -> Set[str]:
    out: Set[str] = set()
    for ln in block:
        m = ASSIGNMENT_RE.match(ln)
        if m:
            out.add(m.group(2))
            continue
        m2 = SET_SUITE_TEST_RE.match(ln)
        if m2:
            raw = m2.group(1)
            mm = re.match(r'^\$\{([A-Za-z0-9_]+)\}$', raw)
            if mm:
                out.add(mm.group(1))
    return out

def _used_vars(block: List[str]) -> Set[str]:
    return set(USAGE_RE.findall("\n".join(block)))

def _http_on_session_calls(block: List[str]) -> List[Tuple[str, str, str, int]]:
    out: List[Tuple[str, str, str, int]] = []
    for idx, ln in enumerate(block):
        m = HTTP_ON_SESSION_RE.search(ln)
        if m:
            out.append((m.group(1).lower(), m.group(2).strip(), m.group(3).strip(), idx))
    return out

def _get_full_http_calls(block: List[str]) -> List[Tuple[str, str, int]]:
    out: List[Tuple[str, str, int]] = []
    for idx, ln in enumerate(block):
        m = GET_FULL_URL_RE.search(ln)
        if m:
            method = m.group(1).lower()
            arg = m.group(2).strip()
            if not re.search(r'on\s+session', arg, re.I):
                out.append((method, arg, idx))
    return out

def _extract_vars_from_call_line(line: str) -> Set[str]:
    ln = re.sub(r'^\s*\$\{[A-Za-z0-9_]+\}\s*=\s*', '', line)
    parts = re.split(r'\s{2,}|\t', ln.strip())
    vars_found: Set[str] = set()
    for p in parts[1:]:
        if p:
            vars_found.update(USAGE_RE.findall(p))
    return vars_found

def _called_keywords(block: List[str]) -> List[Tuple[str, Set[str], int]]:
    called: List[Tuple[str, Set[str], int]] = []
    for idx, ln in enumerate(block):
        if not ln.strip() or ln == ln.lstrip():
            continue
        ln_no_assign = re.sub(r'^\s*\$\{[A-Za-z0-9_]+\}\s*=\s*', '', ln)
        parts = re.split(r'\s{2,}|\t', ln_no_assign.strip())
        if not parts:
            continue
        kw_name = parts[0].strip().lower()
        arg_vars = set(USAGE_RE.findall("\n".join(parts[1:])))
        arg_vars |= _extract_vars_from_call_line(ln)
        called.append((kw_name, arg_vars, idx))
    return called

def _normalize_default(val):
    if val is None:
        return None
    m = re.match(r'^\$\{(.+)\}$', str(val))
    if m:
        return m.group(1)
    return val

# ------------------------- main analyzer -------------------------
def get_case_inputs_for_content(content: str, case_name: str) -> Dict[str, Any]: # pylint: disable=too-many-locals,too-many-statements
    """
    Analyze a Robot Framework test case and extract candidate input variables 
    along with parsing diagnostics.

    Returns:
        Dict with:
            - inputs: List of variable metadata
            - parsing_notes: Dictionary of diagnostic information
    """
    declared = _declared_vars(content)
    for v in declared.values():
        v['default'] = _normalize_default(v.get('default'))

    test_block = _find_test_block(content, case_name)
    notes: Dict[str, Any] = {
        "found_block": bool(test_block),
        "declared_vars": sorted(declared.keys())
    }
    if not test_block:
        notes["message"] = "test case block not found"
        return {"inputs": [], "parsing_notes": notes}

    kw_map = _parse_keywords(content)
    sessions = _sessions_map(content)
    assigned_in_test = _assigned_vars(test_block)
    used_in_test = _used_vars(test_block)

    # -------------------- helpers --------------------
    candidates: Dict[str, Dict] = {}
    visited_kw: Set[str] = set()
    visited_order: List[str] = []
    path_vars: Set[str] = set()
    session_url_vars: Set[str] = set()
    assigned_in_visited_keywords: Set[str] = set()

    def _process_http(block: List[str], label: str):
        """Collect variables from HTTP calls and sessions."""
        for method, sess, path, idx in _http_on_session_calls(block):
            for pv in USAGE_RE.findall(path):
                candidates[pv] = {
                    "name": pv,
                    "default": declared.get(pv, {}).get("default"),
                    "reason": f"used in {method.upper()} \
                        path '{path}' for session '{sess}' (from {label})",
                    "found_in_line": idx,
                }
                path_vars.add(pv)
            if sess in sessions:
                url_expr = sessions[sess]
                mm = re.match(r'^\$\{([A-Za-z0-9_]+)\}$', url_expr)
                if mm:
                    url_var = mm.group(1)
                    candidates[url_var] = {
                        "name": url_var,
                        "default": declared.get(url_var, {}).get("default"),
                        "reason": f"session '{sess}' base URL (from {label})"
                    }
                    session_url_vars.add(url_var)
                else:
                    for iv in USAGE_RE.findall(url_expr):
                        candidates[iv] = {
                            "name": iv,
                            "default": declared.get(iv, {}).get("default"),
                            "reason": f"variable in session '{sess}' URL expression (from {label})"
                        }
                        session_url_vars.add(iv)

        for method, expr, idx in _get_full_http_calls(block):
            for pv in USAGE_RE.findall(expr):
                candidates[pv] = {
                    "name": pv,
                    "default": declared.get(pv, {}).get("default"),
                    "reason": f"used in {method.upper()} URL expression '{expr}' (from {label})",
                    "found_in_line": idx,
                }
                path_vars.add(pv)

    def _process_keywords(block: List[str], label: str):
        """Recursively collect variables from called keywords."""
        for called, arg_vars, idx in _called_keywords(block):
            for av in arg_vars:
                candidates.setdefault(av, {
                    "name": av,
                    "default": declared.get(av, {}).get("default"),
                    "reason": f"passed as argument to keyword '{called}' (from {label})",
                    "found_in_line": idx,
                })
            if called in visited_kw:
                continue
            cand_keys = [k for k in kw_map
                         if k == called or k.startswith(called) or called.startswith(k)]
            if not cand_keys:
                cand_keys = [k for k in kw_map if called in k or k in called]
            for cand in cand_keys:
                if cand not in visited_kw:
                    visited_kw.add(cand)
                    visited_order.append(cand)
                    _process_keywords(kw_map[cand], f"keyword:{cand}")

    def _cleanup_candidates():
        """Remove variables that are assigned in test or keywords."""
        for a in assigned_in_test | assigned_in_visited_keywords:
            candidates.pop(a, None)
            path_vars.discard(a)
            session_url_vars.discard(a)

    def _compute_allowed() -> Set[str]:
        """Compute allowed variables used in test/keywords/sessions."""
        used_in_visited: Set[str] = set()
        for vk in visited_order:
            used_in_visited |= _used_vars(kw_map.get(vk, []))
        allowed: Set[str] = path_vars \
            | session_url_vars | {v for v in (used_in_test | used_in_visited) if v in declared}
        for sess_val in sessions.values():
            for var in USAGE_RE.findall(sess_val):
                if var in declared:
                    allowed.add(var)
        return allowed

    def _collect_final(allowed: Set[str]) -> List[Dict[str, Any]]:
        final_required: Dict[str, Dict] = {}
        for k, val in candidates.items():
            if k in allowed:
                dflt = declared.get(k, {}).get('default') if k in declared else val.get('default')
                final_required[k] = {
                    "name": k,
                    "default": _normalize_default(dflt) if dflt is not None else None,
                    "reason": val.get("reason"),
                    **({"found_in_line": val["found_in_line"]} if "found_in_line" in val else {})
                }
        # fallback
        for k in sorted(allowed):
            if k not in final_required and k in declared:
                final_required[k] = {
                    "name": k,
                    "default": _normalize_default(declared[k].get('default')),
                    "reason": "declared and used in test/keywords (fallback)"
                }
        return [final_required[k] for k in sorted(final_required.keys())]

    # -------------------- main flow --------------------
    _process_http(test_block, "test_case")
    _process_keywords(test_block, "test_case")
    _cleanup_candidates()
    allowed_vars = _compute_allowed()
    inputs = _collect_final(allowed_vars)

    # -------------------- notes --------------------
    notes.update({
        "visited_keywords": visited_order,
        "all_candidates": sorted(candidates.keys()),
        "path_vars": sorted(path_vars),
        "session_url_vars": sorted(session_url_vars),
        "assigned_in_visited_keywords": sorted(assigned_in_visited_keywords),
        "classified_candidates": sorted([i["name"] for i in inputs]),
        "required_details_sample": {
            k: candidates[k]
            for i, k in enumerate(sorted(candidates.keys())) if i < 12 and k in candidates
            }
    })

    return {"inputs": inputs, "parsing_notes": notes}

# ------------------------- type inference -------------------------
def _infer_type_from_default(value: Any) -> str:
    if value is None:
        return "string"
    s = str(value).strip()
    if s.lower() in ("true", "false"):
        return "boolean"
    if re.fullmatch(r'[+-]?\d+', s):
        return "integer"
    if re.fullmatch(r'[+-]?\d+\.\d+', s):
        return "number"
    if re.match(r'^https?://', s):
        return "url"
    return "string"

# ------------------------- public wrapper -------------------------
def get_required_variables_for_case(content: str, case_name: str, test_id: str) -> Dict:
    """method for getting the required case variables"""
    analyzer = get_case_inputs_for_content(content, case_name)
    inputs = analyzer.get("inputs", [])
    required_vars = []
    for inp in inputs:
        reason = inp.get("reason", "") or ""
        if "(from test_case)" in reason or "(from keyword:" in reason:
            name = inp.get("name")
            default = inp.get("default")
            dtype = _infer_type_from_default(default)
            required_vars.append({
                "name": name,
                "datatype": dtype,
                "default": default,
                "reason": reason
            })
    return {
        "test_id": test_id,
        "case_name": case_name,
        "required_variables": required_vars
    }
