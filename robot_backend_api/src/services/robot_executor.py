"""
Service for executing Robot Framework tests.
"""
import subprocess
import os
import tempfile
import shutil
from typing import Dict, Any, Optional, Tuple
import logging
from ..core.config import settings

logger = logging.getLogger(__name__)


class RobotExecutor:
    """
    Executor for Robot Framework tests.
    Runs tests or specific testcases and captures output.
    """
    
    # PUBLIC_INTERFACE
    def execute_test_file(
        self,
        robot_file_path: str,
        variables: Optional[Dict[str, Any]] = None,
        include_tags: Optional[str] = None,
        exclude_tags: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> Tuple[int, str, str, str]:
        """
        Execute a complete robot test file.
        
        Args:
            robot_file_path: Path to the robot test file
            variables: Dictionary of variables to pass to robot
            include_tags: Comma-separated tags to include
            exclude_tags: Comma-separated tags to exclude
            timeout: Execution timeout in seconds
            
        Returns:
            Tuple containing:
                - Return code (0 for pass, non-zero for fail)
                - Path to log.html
                - Path to output.xml
                - Path to report.html
                
        Raises:
            Exception: If execution fails
        """
        return self._execute(robot_file_path, None, variables, include_tags, exclude_tags, timeout)
    
    # PUBLIC_INTERFACE
    def execute_testcase(
        self,
        robot_file_path: str,
        testcase_name: str,
        variables: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None
    ) -> Tuple[int, str, str, str]:
        """
        Execute a specific testcase from a robot test file.
        
        Args:
            robot_file_path: Path to the robot test file
            testcase_name: Name of the testcase to execute
            variables: Dictionary of variables to pass to robot
            timeout: Execution timeout in seconds
            
        Returns:
            Tuple containing:
                - Return code (0 for pass, non-zero for fail)
                - Path to log.html
                - Path to output.xml
                - Path to report.html
                
        Raises:
            Exception: If execution fails
        """
        return self._execute(robot_file_path, testcase_name, variables, None, None, timeout)
    
    def _execute(
        self,
        robot_file_path: str,
        testcase_name: Optional[str],
        variables: Optional[Dict[str, Any]],
        include_tags: Optional[str],
        exclude_tags: Optional[str],
        timeout: Optional[int]
    ) -> Tuple[int, str, str, str]:
        """
        Internal method to execute robot tests.
        """
        output_dir = tempfile.mkdtemp(prefix="robot_run_")
        
        try:
            # Build robot command
            cmd = ["robot"]
            
            # Add output directory
            cmd.extend(["--outputdir", output_dir])
            
            # Add variables
            if variables:
                for key, value in variables.items():
                    cmd.extend(["--variable", f"{key}:{value}"])
            
            # Add tags
            if include_tags:
                for tag in include_tags.split(','):
                    cmd.extend(["--include", tag.strip()])
            
            if exclude_tags:
                for tag in exclude_tags.split(','):
                    cmd.extend(["--exclude", tag.strip()])
            
            # Add specific testcase
            if testcase_name:
                cmd.extend(["--test", testcase_name])
            
            # Add test file
            cmd.append(robot_file_path)
            
            # Execute with timeout
            exec_timeout = timeout or settings.robot_execution_timeout
            logger.info(f"Executing robot command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                timeout=exec_timeout,
                capture_output=True,
                text=True
            )
            
            # Get output file paths
            log_path = os.path.join(output_dir, "log.html")
            output_path = os.path.join(output_dir, "output.xml")
            report_path = os.path.join(output_dir, "report.html")
            
            logger.info(f"Robot execution completed with return code: {result.returncode}")
            return result.returncode, log_path, output_path, report_path
            
        except subprocess.TimeoutExpired:
            logger.error(f"Robot execution timed out after {exec_timeout} seconds")
            raise Exception(f"Execution timed out after {exec_timeout} seconds")
        except Exception as e:
            logger.error(f"Error executing robot tests: {e}")
            # Cleanup temp directory on error
            if os.path.exists(output_dir):
                shutil.rmtree(output_dir, ignore_errors=True)
            raise


# Global executor instance
robot_executor = RobotExecutor()
