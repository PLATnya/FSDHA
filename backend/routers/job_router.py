from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.validation import validate_request_job_id
from pathlib import Path
import logging

from controllers.job_controller import JobController
from services.file_service import FileService
from schemas.validation import FileUploadValidation, validate_job_id
from db_session import get_db
from middleware.error_handler import get_request_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

UPLOAD_DIR = Path("uploads")
file_service = FileService(UPLOAD_DIR)
job_controller = JobController(file_service)

@router.get("")
async def list_jobs(request: Request, db: AsyncSession = Depends(get_db)):
    request_id = get_request_id(request)
    logger.info(f"Listing all jobs", extra={"request_id": request_id})
    
    result = await job_controller.list_jobs(db)
    logger.debug(f"Successfully retrieved jobs list", extra={"request_id": request_id})
    return result

@router.post("/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    request_id = get_request_id(request)
    logger.info(f"File upload request: {file.filename}", extra={"request_id": request_id})
    
    validated_filename, file_size = await FileUploadValidation.validate_file_upload(file)
    logger.debug(f"File validation passed: {validated_filename}, size: {file_size} bytes", extra={"request_id": request_id})

    result = await job_controller.upload_file(file, db)
    return result

@router.get("/id")
async def get_last_id(request: Request, db: AsyncSession = Depends(get_db)):
    request_id = get_request_id(request)
    logger.info(f"Getting last job ID", extra={"request_id": request_id})

    result = await job_controller.get_last_job_id(db)
    logger.debug(f"Successfully retrieved last job ID", extra={"request_id": request_id})
    return result

@router.delete("/reset")
async def reset_all_data(request: Request, db: AsyncSession = Depends(get_db)):
    request_id = get_request_id(request)
    logger.warning(f"Reset all data request", extra={"request_id": request_id})

    result = await job_controller.reset_all_data(db)
    logger.info(f"Successfully reset all data", extra={"request_id": request_id})
    return result


@router.get("/{job_id}")
async def get_job(
    request: Request,
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    request_id = get_request_id(request)
    logger.info(f"Getting job: {job_id}", extra={"request_id": request_id, "job_id": job_id})
    
    validated_job_id = validate_request_job_id(job_id)
    
    result = await job_controller.get_job(validated_job_id, db)
    logger.debug(f"Successfully retrieved job: {validated_job_id}", extra={"request_id": request_id, "job_id": validated_job_id})
    return result


@router.get("/{job_id}/error-report")
async def get_job_error_report(
    request: Request,
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    request_id = get_request_id(request)
    logger.info(f"Getting error report for job: {job_id}", extra={"request_id": request_id, "job_id": job_id})
    
    validated_job_id = validate_request_job_id(job_id)
    
    result = await job_controller.get_job_error_report(validated_job_id, db)
    logger.debug(f"Successfully generated error report for job: {validated_job_id}", extra={"request_id": request_id, "job_id": validated_job_id})
    return result
