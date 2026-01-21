from fastapi import UploadFile, HTTPException
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List
import asyncio
import logging
import csv
import io

from services.job_service import JobService
from services.file_service import FileService
from database import Job

logger = logging.getLogger(__name__)


class JobController:
    def __init__(self, file_service: FileService):
        self.file_service = file_service
        self._tasks: Dict[str, asyncio.Task] = {}

    def _register_task(self, job_id: str, task: asyncio.Task) -> None:
        self._tasks[job_id] = task

        def _cleanup(_task: asyncio.Task) -> None:
            self._tasks.pop(job_id, None)

        task.add_done_callback(_cleanup)

    async def _cancel_all_tasks(self, timeout_seconds: float = 5.0) -> int:
        tasks = list(self._tasks.values())
        if not tasks:
            return 0
        for t in tasks:
            t.cancel()
        try:
            await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            logger.warning("Timed out waiting for job tasks to cancel")
        finally:
            self._tasks.clear()
        return len(tasks)

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
            
            async def runner():
                try:
                    await JobService.process_job_async(str(file_path), job._id)
                except asyncio.CancelledError:
                    logger.info(f"Background task cancelled for job {job._id}")
                    raise
                except Exception as e:
                    logger.error(f"Unhandled error in background task for job {job._id}: {e}", exc_info=True)

            task = asyncio.create_task(runner(), name=f"process_job:{job._id}")
            self._register_task(job._id, task)
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

    async def reset_all_data(self, db: AsyncSession) -> JSONResponse:
        try:
            cancelled = await self._cancel_all_tasks()
            deleted = await JobService.delete_all_job_data(db)
            return JSONResponse(
                status_code=200,
                content={
                    "message": "All job-related data deleted",
                    "cancelled_tasks": cancelled,
                    **deleted,
                }
            )
        except Exception as e:
            logger.error(f"Error resetting all data: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error resetting all data: {str(e)}")

    async def get_job(
        self,
        job_id: str,
        db: AsyncSession
    ) -> JSONResponse:
        try:
            job = await JobService.get_job_by_id(db, job_id)
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")
            error_messages = await JobService.get_job_errors(db, job._id)
            return JSONResponse(
                status_code=200,
                content=self._serialize_job(job, error_messages)
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving job {job_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error retrieving job: {str(e)}"
            )

    async def get_job_error_report(
        self,
        job_id: str,
        db: AsyncSession
    ) -> Response:
        job = await JobService.get_job_by_id(db, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        error_rows = await JobService.get_error_rows(db, job_id)

        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["rowNumber", "name", "email", "phone", "company", "error"])
        for r in error_rows:
            writer.writerow(
                [
                    r.rowNumber,
                    r.name or "",
                    r.email or "",
                    r.phone or "",
                    r.company or "",
                    JobService._strip_row_prefix(r.error_message) or "",
                ]
            )
        csv_text = out.getvalue()
        out.close()

        filename = f'job_{job_id}_error_report.csv'
        return Response(
            content=csv_text,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
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
