from pathlib import Path
from fastapi import UploadFile
import logging

from exceptions import FileUploadError

logger = logging.getLogger(__name__)


class FileService:
    def __init__(self, upload_dir: Path):
        self.upload_dir = upload_dir
        self.upload_dir.mkdir(exist_ok=True)

    async def save_uploaded_file(
        self,
        file: UploadFile,
        job_id: str
    ) -> Path:
        """
        Save an uploaded file to the upload directory and return the file path.
        Returns the file path.
        Throws FileUploadError on failure.
        """
        if not file.filename:
            logger.warning(f"Attempted to save file without filename for job: {job_id}")
            raise FileUploadError("Filename is required")
        
        file_path = self.upload_dir / f"{job_id}_{file.filename}"
        logger.debug(f"Saving file to: {file_path} for job: {job_id}")
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        logger.info(f"File saved successfully: {file_path} for job: {job_id}")
        return file_path


    def get_file_path(self, job_id: str, filename: str) -> Path:
        """
        Get the file path for a given job and filename.
        Returns the file path.
        """
        return self.upload_dir / f"{job_id}_{filename}"
