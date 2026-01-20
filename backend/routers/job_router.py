from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path

from controllers.job_controller import JobController
from services.file_service import FileService
from db_session import get_db

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

UPLOAD_DIR = Path("uploads")
file_service = FileService(UPLOAD_DIR)
job_controller = JobController(file_service)

@router.get("")
async def list_jobs(db: AsyncSession = Depends(get_db)):
    return await job_controller.list_jobs(db)

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    return await job_controller.upload_file(file, db)

@router.get("/id")
async def get_last_id(db: AsyncSession = Depends(get_db)):
    return await job_controller.get_last_job_id(db)
