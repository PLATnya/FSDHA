from typing import Optional
import logging
import uuid

logger = logging.getLogger(__name__)


def validate_job_id(job_id: str) -> str:
    if not job_id or not isinstance(job_id, str):
        logger.debug(f"Invalid job_id: not a string or empty")
        raise ValueError("job_id must be a non-empty string")
    job_id = job_id.strip()
    if not job_id:
        logger.debug(f"Invalid job_id: empty or whitespace only")
        raise ValueError("job_id cannot be empty or whitespace")

    try:
        uuid.UUID(job_id)
        logger.debug(f"Job ID validation passed: {job_id}")
    except ValueError:
        logger.debug(f"Invalid job_id format: {job_id}")
        raise ValueError(f"job_id must be a valid UUID format, got: {job_id}")
    return job_id

class FileUploadValidation:

    ALLOWED_EXTENSIONS = {'.csv', '.txt'}
    
    # 10mb
    MAX_FILE_SIZE = 10 * 1024 * 1024
    
    MAX_FILENAME_LENGTH = 255
    
    @classmethod
    def validate_filename(cls, filename: Optional[str]) -> str:
        """Validate filename"""
        if not filename:
            logger.debug("Filename validation failed: filename is None")
            raise ValueError("Filename is required")
        
        filename = filename.strip()
        if not filename:
            logger.debug("Filename validation failed: filename is empty after strip")
            raise ValueError("Filename cannot be empty")
        
        if len(filename) > cls.MAX_FILENAME_LENGTH:
            logger.debug(f"Filename validation failed: too long ({len(filename)} > {cls.MAX_FILENAME_LENGTH})")
            raise ValueError(f"Filename too long (max {cls.MAX_FILENAME_LENGTH} characters)")
        
        if '..' in filename or '/' in filename or '\\' in filename:
            logger.debug(f"Filename validation failed: contains invalid characters: {filename}")
            raise ValueError("Filename contains invalid characters")
        
        logger.debug(f"Filename validation passed: {filename}")
        return filename
    
    @classmethod
    def validate_file_extension(cls, filename: str) -> None:
        if not filename:
            logger.debug("File extension validation failed: filename is None")
            raise ValueError("Filename is required")
        
        if '.' not in filename:
            logger.debug(f"File extension validation failed: no extension in {filename}")
            raise ValueError("File must have an extension")
        
        ext = '.' + filename.rsplit('.', 1)[1].lower()
        if ext not in cls.ALLOWED_EXTENSIONS:
            logger.debug(f"File extension validation failed: {ext} not in allowed extensions")
            raise ValueError(
                f"File type not allowed. Allowed types: {', '.join(cls.ALLOWED_EXTENSIONS)}"
            )
        logger.debug(f"File extension validation passed: {ext}")
    
    @classmethod
    def validate_file_size(cls, file_size: int) -> None:
        if file_size <= 0:
            logger.debug(f"File size validation failed: size is {file_size}")
            raise ValueError("File size must be greater than 0")
        
        if file_size > cls.MAX_FILE_SIZE:
            max_mb = cls.MAX_FILE_SIZE / (1024 * 1024)
            logger.debug(f"File size validation failed: {file_size} bytes exceeds {cls.MAX_FILE_SIZE} bytes")
            raise ValueError(f"File size exceeds maximum allowed size of {max_mb}MB")
        logger.debug(f"File size validation passed: {file_size} bytes")
    