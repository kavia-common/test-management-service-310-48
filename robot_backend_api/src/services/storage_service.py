"""
Storage service wrapper providing convenience methods for robot test management.
"""
from ..core.storage import storage_service
import logging

logger = logging.getLogger(__name__)


# PUBLIC_INTERFACE
def save_robot_file(file_data: bytes, test_file_id: int, filename: str) -> str:
    """
    Save a robot test file to storage.
    
    Args:
        file_data: File content as bytes
        test_file_id: Test file ID
        filename: Original filename
        
    Returns:
        str: Storage path
    """
    object_name = f"robot_files/{test_file_id}/{filename}"
    return storage_service.upload_file(file_data, object_name, "text/plain")


# PUBLIC_INTERFACE
def save_run_artifact(file_path: str, run_id: int, artifact_type: str) -> str:
    """
    Save a run artifact (log, output, report) to storage.
    
    Args:
        file_path: Local file path
        run_id: Run ID
        artifact_type: Type of artifact (log, output, report)
        
    Returns:
        str: Storage path
    """
    with open(file_path, 'rb') as f:
        file_data = f.read()
    
    ext = "html" if artifact_type in ["log", "report"] else "xml"
    object_name = f"runs/{run_id}/{artifact_type}.{ext}"
    
    content_type = "text/html" if ext == "html" else "application/xml"
    return storage_service.upload_file(file_data, object_name, content_type)


# PUBLIC_INTERFACE
def get_robot_file(storage_path: str) -> bytes:
    """
    Retrieve a robot test file from storage.
    
    Args:
        storage_path: Storage path
        
    Returns:
        bytes: File content
    """
    return storage_service.get_file(storage_path)


# PUBLIC_INTERFACE
def get_run_logs(run_id: int) -> dict:
    """
    Get presigned URLs for all run artifacts.
    
    Args:
        run_id: Run ID
        
    Returns:
        dict: Dictionary with presigned URLs for log, output, and report
    """
    return {
        'log_url': storage_service.get_presigned_url(f"runs/{run_id}/log.html"),
        'output_url': storage_service.get_presigned_url(f"runs/{run_id}/output.xml"),
        'report_url': storage_service.get_presigned_url(f"runs/{run_id}/report.html")
    }
