"""
Service for parsing Robot Framework test files to extract testcases and variables.
"""
from robot.parsing import get_model
from typing import List, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)


class RobotParser:
    """
    Parser for Robot Framework test files.
    Extracts testcases, variables, and metadata from .robot files.
    """
    
    # PUBLIC_INTERFACE
    def parse_file(self, file_path: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Parse a robot test file and extract testcases and variables.
        
        Args:
            file_path: Path to the .robot file
            
        Returns:
            Tuple containing:
                - List of testcase dictionaries with name, description, and tags
                - List of variable dictionaries with name, default_value, and description
                
        Raises:
            Exception: If parsing fails
        """
        try:
            testcases = []
            variables = []
            
            # Parse using robot.parsing for detailed structure
            model = get_model(file_path)
            
            # Extract variables from Variables section
            for section in model.sections:
                if section.header and hasattr(section.header, 'data_tokens'):
                    header_value = str(section.header.data_tokens[0].value).lower()
                    
                    if 'variable' in header_value:
                        for item in section.body:
                            if hasattr(item, 'tokens') and len(item.tokens) > 0:
                                var_name = str(item.tokens[0].value).strip()
                                var_value = ""
                                var_desc = ""
                                
                                if len(item.tokens) > 1:
                                    var_value = str(item.tokens[1].value).strip()
                                
                                # Get comment as description
                                if len(item.tokens) > 2:
                                    for token in item.tokens[2:]:
                                        if hasattr(token, 'type') and token.type == 'COMMENT':
                                            var_desc = str(token.value).strip('#').strip()
                                            break
                                
                                if var_name and (var_name.startswith('${') or var_name.startswith('@{')):
                                    variables.append({
                                        'name': var_name,
                                        'default_value': var_value,
                                        'description': var_desc
                                    })
                    
                    elif 'test case' in header_value:
                        for item in section.body:
                            if hasattr(item, 'name'):
                                tc_name = str(item.name).strip()
                                tc_desc = ""
                                tc_tags = []
                                
                                # Get documentation and tags
                                if hasattr(item, 'body'):
                                    for step in item.body:
                                        if hasattr(step, 'type'):
                                            if step.type == 'DOCUMENTATION':
                                                if hasattr(step, 'tokens') and len(step.tokens) > 1:
                                                    tc_desc = str(step.tokens[1].value).strip()
                                            elif step.type == 'TAGS':
                                                if hasattr(step, 'tokens'):
                                                    tc_tags = [str(t.value).strip() for t in step.tokens[1:] 
                                                              if hasattr(t, 'value') and str(t.value).strip()]
                                
                                testcases.append({
                                    'name': tc_name,
                                    'description': tc_desc,
                                    'tags': ','.join(tc_tags) if tc_tags else None
                                })
            
            logger.info(f"Parsed {len(testcases)} testcases and {len(variables)} variables from {file_path}")
            return testcases, variables
            
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
