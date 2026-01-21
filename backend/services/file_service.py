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
        try:
            if not file.filename:
                raise FileUploadError("Filename is required")
            
            file_path = self.upload_dir / f"{job_id}_{file.filename}"
            
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            
            return file_path
        except FileUploadError:
            raise
        except Exception as e:
            raise FileUploadError(f"Failed to save file: {str(e)}")

    def get_file_path(self, job_id: str, filename: str) -> Path:
        return self.upload_dir / f"{job_id}_{filename}"
