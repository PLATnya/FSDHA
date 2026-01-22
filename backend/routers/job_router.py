from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
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
    try:
        result = await job_controller.list_jobs(db)
        logger.debug(f"Successfully retrieved jobs list", extra={"request_id": request_id})
        return result
    except Exception as e:
        logger.error(f"Failed to list jobs: {e}", exc_info=True, extra={"request_id": request_id})
        raise

@router.post("/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    request_id = get_request_id(request)
    logger.info(f"File upload request: {file.filename}", extra={"request_id": request_id, "filename": file.filename})
    
    try:
        validated_filename = FileUploadValidation.validate_filename(file.filename)
        FileUploadValidation.validate_file_extension(validated_filename)

        content = await file.read()
        file_size = len(content)
        FileUploadValidation.validate_file_size(file_size)
        
        await file.seek(0)
        logger.debug(f"File validation passed: {validated_filename}, size: {file_size} bytes", extra={"request_id": request_id})

    except ValueError as e:
        logger.warning(f"File validation failed: {str(e)}", extra={"request_id": request_id, "filename": file.filename})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error reading file: {e}", exc_info=True, extra={"request_id": request_id, "filename": file.filename})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error reading file: {str(e)}"
        )
    
    return await job_controller.upload_file(file, db)

@router.get("/id")
async def get_last_id(request: Request, db: AsyncSession = Depends(get_db)):
    request_id = get_request_id(request)
    logger.info(f"Getting last job ID", extra={"request_id": request_id})
    try:
        result = await job_controller.get_last_job_id(db)
        logger.debug(f"Successfully retrieved last job ID", extra={"request_id": request_id})
        return result
    except Exception as e:
        logger.error(f"Failed to get last job ID: {e}", exc_info=True, extra={"request_id": request_id})
        raise

@router.delete("/reset")
async def reset_all_data(request: Request, db: AsyncSession = Depends(get_db)):
    request_id = get_request_id(request)
    logger.warning(f"Reset all data request", extra={"request_id": request_id})
    try:
        result = await job_controller.reset_all_data(db)
        logger.info(f"Successfully reset all data", extra={"request_id": request_id})
        return result
    except Exception as e:
        logger.error(f"Failed to reset all data: {e}", exc_info=True, extra={"request_id": request_id})
        raise


@router.get("/{job_id}")
async def get_job(
    request: Request,
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    request_id = get_request_id(request)
    logger.info(f"Getting job: {job_id}", extra={"request_id": request_id, "job_id": job_id})
    
    try:
        validated_job_id = validate_job_id(job_id)
    except ValueError as e:
        logger.warning(f"Invalid job_id format: {job_id} - {str(e)}", extra={"request_id": request_id, "job_id": job_id})
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    
    try:
        result = await job_controller.get_job(validated_job_id, db)
        logger.debug(f"Successfully retrieved job: {validated_job_id}", extra={"request_id": request_id, "job_id": validated_job_id})
        return result
    except Exception as e:
        logger.error(f"Failed to get job {validated_job_id}: {e}", exc_info=True, extra={"request_id": request_id, "job_id": validated_job_id})
        raise


@router.get("/{job_id}/error-report")
async def get_job_error_report(
    request: Request,
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    request_id = get_request_id(request)
    logger.info(f"Getting error report for job: {job_id}", extra={"request_id": request_id, "job_id": job_id})
    
    try:
        validated_job_id = validate_job_id(job_id)
    except ValueError as e:
        logger.warning(f"Invalid job_id format: {job_id} - {str(e)}", extra={"request_id": request_id, "job_id": job_id})
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    
    try:
        result = await job_controller.get_job_error_report(validated_job_id, db)
        logger.debug(f"Successfully generated error report for job: {validated_job_id}", extra={"request_id": request_id, "job_id": validated_job_id})
        return result
    except Exception as e:
        logger.error(f"Failed to get error report for job {validated_job_id}: {e}", exc_info=True, extra={"request_id": request_id, "job_id": validated_job_id})
        raise
