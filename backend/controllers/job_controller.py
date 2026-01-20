from fastapi import UploadFile, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List
import asyncio
import logging

from services.job_service import JobService
from services.file_service import FileService
from database import Job

logger = logging.getLogger(__name__)


class JobController:
    def __init__(self, file_service: FileService):
        self.file_service = file_service

    def _serialize_job(self, job: Job, errors: List[str]) -> Dict[str, Any]:
        return {
            "id": job._id,
            "filename": job.filename,
            "status": job.status.value,
            "totalRows": job.totalRows,
            "processedRows": job.processedRows,
            "successCount": job.successCount,
            "failedCount": job.failedCount,
            "errors": errors,
            "createdAt": job.createdAt.isoformat() if job.createdAt else None,
            "completedAt": job.completedAt.isoformat() if job.completedAt else None,
        }

    async def upload_file(
        self,
        file: UploadFile,
        db: AsyncSession
    ) -> JSONResponse:
        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="Filename is required"
            )
        try:
            job = await JobService.create_job(
                db=db,
                filename=file.filename
            )
            file_path = await self.file_service.save_uploaded_file(
                file=file,
                job_id=job._id
            )
            
            async def process_with_error_handling():
                try:
                    await JobService.process_job_async(str(file_path), job._id)
                except Exception as e:
                    logger.error(f"Unhandled error in background task for job {job._id}: {e}", exc_info=True)
            
            asyncio.create_task(process_with_error_handling())
            logger.info(f"File uploaded successfully: {file.filename} (job_id: {job._id}), background task started")
            return JSONResponse(
                status_code=200,
                content={
                    "id": job._id,
                    "filename": job.filename,
                    "status": job.status.value,
                    "message": "File uploaded successfully and queued for processing"
                }
            )
        except HTTPException:
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Error uploading file {file.filename}: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error uploading file: {str(e)}"
            )

    async def list_jobs(
        self,
        db: AsyncSession
    ) -> JSONResponse:
        try:
            jobs = await JobService.get_all_jobs(db)
            job_ids = [job._id for job in jobs]
            all_errors = await JobService.get_job_errors_batch(db, job_ids)
            jobs_list = [
                self._serialize_job(job, all_errors.get(job._id, []))
                for job in jobs
            ]
            logger.debug(f"Retrieved {len(jobs_list)} jobs")
            return JSONResponse(
                status_code=200,
                content={
                    "jobs": jobs_list,
                    "total": len(jobs_list)
                }
            )
        except Exception as e:
            logger.error(f"Error retrieving jobs: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error retrieving jobs: {str(e)}"
            )

    async def get_last_job_id(
        self,
        db: AsyncSession
    ) -> JSONResponse:
        try:
            last_job = await JobService.get_last_job(db)
            if not last_job:
                return JSONResponse(
                    status_code=200,
                    content={
                        "last_id": None,
                        "message": "No jobs in queue",
                        "total_jobs": 0
                    }
                )
            error_messages = await JobService.get_job_errors(db, last_job._id)
            return JSONResponse(
                status_code=200,
                content=self._serialize_job(last_job, error_messages)
            )
        except Exception as e:
            logger.error(f"Error retrieving last job ID: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error retrieving last job ID: {str(e)}"
            )
