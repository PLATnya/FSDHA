from fastapi import HTTPException, status

class JobNotFoundError(HTTPException):
    """
    Exception raised when a job with the given job_id is not found.

    Args:
        job_id (str): The ID of the job that was not found.

    Returns:
        404 HTTPException with detail indicating missing job.
    """
    def __init__(self, job_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {job_id}"
        )


class JobValidationError(HTTPException):
    """
    Exception raised when a job fails validation (e.g. invalid input data).

    Args:
        message (str): Description of the validation error.

    Returns:
        400 HTTPException indicating validation failure.
    """
    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job validation error: {message}"
        )


class JobProcessingError(HTTPException):
    """
    Exception raised when there is an error processing a job.

    Args:
        job_id (str): The ID of the job that failed to process.
        message (str): Description of the processing error.

    Returns:
        500 HTTPException indicating a processing error.
    """
    def __init__(self, job_id: str, message: str):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Job processing error for job {job_id}: {message}"
        )


class FileUploadError(HTTPException):
    """
    Exception raised on file upload errors (e.g. invalid file, format, etc.).

    Args:
        message (str): Description of the file upload error.

    Returns:
        400 HTTPException indicating a file upload failure.
    """
    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File upload error: {message}"
        )


class DatabaseError(HTTPException):
    """
    Exception raised for database-related errors (e.g. connectivity, query failure).

    Args:
        message (str): Description of the database error.

    Returns:
        500 HTTPException indicating a database error.
    """
    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {message}"
        )
