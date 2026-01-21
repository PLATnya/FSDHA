from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path

from controllers.job_controller import JobController
from services.file_service import FileService
from schemas.validation import FileUploadValidation, validate_job_id
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

    try:
        validated_filename = FileUploadValidation.validate_filename(file.filename)
        FileUploadValidation.validate_file_extension(validated_filename)

        content = await file.read()
        file_size = len(content)
        FileUploadValidation.validate_file_size(file_size)
        
        await file.seek(0)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error reading file: {str(e)}"
        )
    
    return await job_controller.upload_file(file, db)

@router.get("/id")
async def get_last_id(db: AsyncSession = Depends(get_db)):
    return await job_controller.get_last_job_id(db)

@router.delete("/reset")
async def reset_all_data(db: AsyncSession = Depends(get_db)):
    return await job_controller.reset_all_data(db)


@router.get("/{job_id}")
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    try:
        validated_job_id = validate_job_id(job_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    return await job_controller.get_job(validated_job_id, db)


@router.get("/{job_id}/error-report")
async def get_job_error_report(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    try:
        validated_job_id = validate_job_id(job_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    return await job_controller.get_job_error_report(validated_job_id, db)
