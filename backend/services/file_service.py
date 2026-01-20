from pathlib import Path
from fastapi import UploadFile


class FileService:
    def __init__(self, upload_dir: Path):
        self.upload_dir = upload_dir
        self.upload_dir.mkdir(exist_ok=True)

    async def save_uploaded_file(
        self,
        file: UploadFile,
        job_id: str
    ) -> Path:
        file_path = self.upload_dir / f"{job_id}_{file.filename}"
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        return file_path

    def get_file_path(self, job_id: str, filename: str) -> Path:
        return self.upload_dir / f"{job_id}_{filename}"
