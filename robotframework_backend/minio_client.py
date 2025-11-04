"""
MinIO client wrapper for uploading, downloading, and managing objects
in the configured MinIO bucket.
"""

import os
import io
from datetime import timedelta
from typing import BinaryIO

from minio import Minio
from minio.error import S3Error

# ----------------------------
# MinIO configuration
# ----------------------------
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "127.1.0.0:9001")  # Changed to API port
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "robot-tests")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() in ("1", "true", "yes")

_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=MINIO_SECURE,
)

# ----------------------------
# Helper functions
# ----------------------------


def ensure_bucket() -> None:
    """
    Ensure that the configured bucket exists in MinIO.
    Creates the bucket if it does not exist.
    """
    try:
        if not _client.bucket_exists(MINIO_BUCKET):
            _client.make_bucket(MINIO_BUCKET)
    except S3Error as exc:
        raise RuntimeError(f"Failed to ensure bucket {MINIO_BUCKET}") from exc


def put_object(
    object_name: str,
    data: BinaryIO,
    length: int,
    content_type: str = "application/octet-stream",
) -> None:
    """
    Upload a file-like object to MinIO (stream).
    """
    try:
        ensure_bucket()
        _client.put_object(
            MINIO_BUCKET, object_name, data, length, content_type=content_type
        )
    except S3Error as exc:
        raise RuntimeError(f"Failed to upload object {object_name}") from exc


def put_bytes(
    object_name: str, data_bytes: bytes, content_type: str = "application/octet-stream"
) -> None:
    """
    Upload raw bytes to MinIO (convenience wrapper).
    """
    bio = io.BytesIO(data_bytes)
    put_object(object_name, bio, len(data_bytes), content_type=content_type)


def get_object_to_bytes(object_name: str) -> bytes:
    """
    Download an object from MinIO and return its bytes content.
    """
    try:
        response = _client.get_object(MINIO_BUCKET, object_name)
        with response as stream:
            return stream.read()
    except S3Error as exc:
        raise RuntimeError(f"Failed to fetch object {object_name}") from exc


def remove_object(object_name: str) -> None:
    """
    Remove an object from MinIO.
    """
    try:
        _client.remove_object(MINIO_BUCKET, object_name)
    except S3Error as exc:
        raise RuntimeError(f"Failed to remove object {object_name}") from exc


def presigned_get_url(object_name: str, expires_seconds: int = 3600) -> str:
    """
    Return a presigned GET URL valid for `expires_seconds` seconds.
    """
    try:
        return _client.presigned_get_object(
            MINIO_BUCKET, object_name, expires=timedelta(seconds=expires_seconds)
        )
    except S3Error as exc:
        raise RuntimeError(
            f"Failed to generate presigned URL for object {object_name}"
        ) from exc
