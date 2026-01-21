from fastapi import HTTPException, status
from typing import Optional, Dict, Any


class JobNotFoundError(HTTPException):
    def __init__(self, job_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {job_id}"
        )


class JobValidationError(HTTPException):
    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job validation error: {message}"
        )


class JobProcessingError(HTTPException):
    def __init__(self, job_id: str, message: str):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Job processing error for job {job_id}: {message}"
        )


class FileUploadError(HTTPException):
    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File upload error: {message}"
        )


class DatabaseError(HTTPException):
    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {message}"
        )
