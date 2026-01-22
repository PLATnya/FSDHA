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
from database import Job, JobError
from exceptions import JobNotFoundError, FileUploadError, DatabaseError

logger = logging.getLogger(__name__)


class JobController:
    def __init__(self, file_service: FileService):
        """
        Initialize JobController with a FileService instance.
        Maintains a dict of running background tasks keyed by job_id.
        """
        self.file_service = file_service
        self._tasks: Dict[str, asyncio.Task] = {}

    def _register_task(self, job_id: str, task: asyncio.Task) -> None:
        """
        Register a new background task for a job, and ensure it's cleaned up on completion.
        """
        self._tasks[job_id] = task

        def _cleanup(_task: asyncio.Task) -> None:
            # Remove the task from the _tasks dict when it finishes.
            self._tasks.pop(job_id, None)

        task.add_done_callback(_cleanup)

    async def _cancel_all_tasks(self, timeout_seconds: float = 5.0) -> int:
        """
        Cancel and wait for all running background tasks.
        Returns the number of cancelled tasks.
        """
        tasks = list(self._tasks.values())
        if not tasks:
            return 0
        for t in tasks:
            t.cancel()  # Request cancellation
        try:
            # Wait for all tasks to complete within the timeout
            await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            logger.warning("Timed out waiting for job tasks to cancel")
        finally:
            self._tasks.clear()
        return len(tasks)

    def _serialize_job(self, job: Job, errors: List[str]) -> Dict[str, Any]:
        """
        Convert a Job ORM instance and list of errors into a serializable dict structure.
        """
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
        """
        Handle an upload request: create a DB job, save file, and queue for processing in a background task.
        Returns a JSONResponse with job info.
        """
        if not file.filename:
            logger.warning("File upload attempted without filename")
            raise FileUploadError("Filename is required")
        try:
            logger.debug(f"Creating job for file: {file.filename}")
            # 1. Create the job in the database
            job = await JobService.create_job(
                db=db,
                filename=file.filename
            )
            logger.debug(f"Job created: {job._id}, saving file")
            # 2. Save the uploaded file to disk
            file_path = await self.file_service.save_uploaded_file(
                file=file,
                job_id=job._id
            )
            logger.debug(f"File saved to: {file_path}")
            
            # 3. Start a background task to process the file
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
        except Exception as e:
            # Rollback DB transaction on any failure
            await db.rollback()
            raise FileUploadError(f"Failed to upload file: {str(e)}")

    async def list_jobs(
        self,
        db: AsyncSession
    ) -> JSONResponse:
        """
        Return a JSON list of all jobs, with error info for each.
        """
        try:
            logger.debug("Fetching all jobs from database")
            jobs = await JobService.get_all_jobs(db)

            job_ids = [job._id for job in jobs]
            logger.debug(f"Found {len(job_ids)} jobs, fetching errors")

            # Retrieve errors for all jobs in a single batch query
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
            raise DatabaseError(f"Failed to retrieve jobs: {str(e)}")

    async def reset_all_data(self, db: AsyncSession) -> JSONResponse:
        """
        Cancel all running background tasks and delete all job-related data.
        """
        try:
            logger.info("Starting reset all data operation")
            cancelled = await self._cancel_all_tasks()  # Cancel background tasks

            logger.info(f"Cancelled {cancelled} background tasks")
            deleted = await JobService.delete_all_job_data(db)  # Delete jobs in database

            logger.info(f"Reset completed: {deleted}")
            return JSONResponse(
                status_code=200,
                content={
                    "message": "All job-related data deleted",
                    "cancelled_tasks": cancelled,
                    **deleted,
                }
            )
        except Exception as e:
            raise DatabaseError(f"Failed to reset all data: {str(e)}")

    async def get_job(
        self,
        job_id: str,
        db: AsyncSession
    ) -> JSONResponse:
        """
        Return details for a single job, including error info.
        """
        try:
            logger.debug(f"Fetching job: {job_id}")
            job = await JobService.get_job_by_id(db, job_id)

            if not job:
                logger.warning(f"Job not found: {job_id}")
                raise JobNotFoundError(job_id)

            error_messages = await JobService.get_job_errors(db, job._id)
            logger.debug(f"Retrieved job {job_id} with {len(error_messages)} errors")
            return JSONResponse(
                status_code=200,
                content=self._serialize_job(job, error_messages)
            )
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve job: {str(e)}")

    def _generate_error_report_csv(self, error_rows: List[JobError]) -> str:
        """
        Generate CSV content from a list of JobError rows.
        The CSV contains standard columns for customer info and error details.
        """
        with io.StringIO() as out:
            writer = csv.writer(out)
            # Write CSV header
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
            return out.getvalue()

    async def get_job_error_report(
        self,
        job_id: str,
        db: AsyncSession
    ) -> Response:
        """
        Generate and return a CSV error report for the given job.
        Prompts browser to download the CSV as a file.
        """
        try:
            logger.debug(f"Generating error report for job: {job_id}")
            job = await JobService.get_job_by_id(db, job_id)
            
            if not job:
                logger.warning(f"Job not found for error report: {job_id}")
                raise JobNotFoundError(job_id)

            # Get all error rows for this job to include in the CSV
            error_rows = await JobService.get_error_rows(db, job_id)
            logger.debug(f"Found {len(error_rows)} error rows for job {job_id}")

            csv_content = self._generate_error_report_csv(error_rows)
            filename = f'job_{job_id}_error_report.csv'
            
            logger.info(f"Generated error report for job {job_id}: {len(error_rows)} rows")
            return Response(
                content=csv_content,
                media_type="text/csv",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )

        except Exception as e:
            raise DatabaseError(f"Failed to generate error report: {str(e)}")

    async def get_last_job_id(
        self,
        db: AsyncSession
    ) -> JSONResponse:
        """
        Fetch and return the most recently created job (if any).
        """
        try:
            logger.debug("Fetching last job ID")
            last_job = await JobService.get_last_job(db)
            
            if not last_job:
                logger.debug("No jobs found in queue")
                return JSONResponse(
                    status_code=200,
                    content={
                        "last_id": None,
                        "message": "No jobs in queue",
                        "total_jobs": 0
                    }
                )
            error_messages = await JobService.get_job_errors(db, last_job._id)
            logger.debug(f"Retrieved last job: {last_job._id}")
            return JSONResponse(
                status_code=200,
                content=self._serialize_job(last_job, error_messages)
            )
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve last job ID: {str(e)}")
