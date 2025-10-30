"""
MinIO storage service for managing robot files and execution logs.
"""
from minio import Minio
from minio.error import S3Error
from io import BytesIO
from typing import Optional
import logging
from .config import settings

logger = logging.getLogger(__name__)


class StorageService:
    """
    Service for interacting with MinIO object storage.
    Handles upload and retrieval of robot test files and execution logs.
    """
    
    def __init__(self):
        """Initialize MinIO client with configured credentials."""
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure
        )
        self.bucket_name = settings.minio_bucket_name
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self) -> None:
        """Create bucket if it doesn't exist."""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Created bucket: {self.bucket_name}")
        except S3Error as e:
            logger.error(f"Error ensuring bucket exists: {e}")
            raise
    
    # PUBLIC_INTERFACE
    def upload_file(self, file_data: bytes, object_name: str, content_type: str = "application/octet-stream") -> str:
        """
        Upload a file to MinIO storage.
        
        Args:
            file_data: File content as bytes
            object_name: Object name/path in storage
            content_type: MIME type of the file
            
        Returns:
            str: Object name/path in storage
            
        Raises:
            S3Error: If upload fails
        """
        try:
            data_stream = BytesIO(file_data)
            self.client.put_object(
                self.bucket_name,
                object_name,
                data_stream,
                length=len(file_data),
                content_type=content_type
            )
            logger.info(f"Uploaded file: {object_name}")
            return object_name
        except S3Error as e:
            logger.error(f"Error uploading file {object_name}: {e}")
            raise
    
    # PUBLIC_INTERFACE
    def get_file(self, object_name: str) -> Optional[bytes]:
        """
        Retrieve a file from MinIO storage.
        
        Args:
            object_name: Object name/path in storage
            
        Returns:
            Optional[bytes]: File content as bytes, or None if not found
        """
        try:
            response = self.client.get_object(self.bucket_name, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as e:
            logger.error(f"Error retrieving file {object_name}: {e}")
            return None
    
    # PUBLIC_INTERFACE
    def delete_file(self, object_name: str) -> bool:
        """
        Delete a file from MinIO storage.
        
        Args:
            object_name: Object name/path in storage
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.client.remove_object(self.bucket_name, object_name)
            logger.info(f"Deleted file: {object_name}")
            return True
        except S3Error as e:
            logger.error(f"Error deleting file {object_name}: {e}")
            return False
    
    # PUBLIC_INTERFACE
    def get_presigned_url(self, object_name: str, expiry_seconds: int = 3600) -> Optional[str]:
        """
        Get a presigned URL for accessing a file.
        
        Args:
            object_name: Object name/path in storage
            expiry_seconds: URL expiration time in seconds
            
        Returns:
            Optional[str]: Presigned URL, or None if error
        """
        try:
            from datetime import timedelta
            url = self.client.presigned_get_object(
                self.bucket_name,
                object_name,
                expires=timedelta(seconds=expiry_seconds)
            )
            return url
        except S3Error as e:
            logger.error(f"Error generating presigned URL for {object_name}: {e}")
            return None


# Global storage service instance
storage_service = StorageService()
