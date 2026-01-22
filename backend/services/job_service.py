from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, delete
from sqlalchemy.exc import IntegrityError
from typing import Optional, List, Dict, Tuple
from datetime import datetime
import uuid
import csv
import re
from pathlib import Path
import logging
import asyncio

from database import Job, JobError, JobStatus, Customer
from db_session import AsyncSessionLocal
from services.job_progress_hub import job_progress_hub
from exceptions import JobValidationError, FileUploadError

logger = logging.getLogger(__name__)

class JobService:
    @staticmethod
    async def create_job(
        db: AsyncSession,
        filename: str
    ) -> Job:
        job_id = str(uuid.uuid4())
        logger.debug(f"Creating new job: {job_id} for file: {filename}")
        job = Job(
            _id=job_id,
            filename=filename,
            status=JobStatus.PENDING,
            totalRows=0,
            processedRows=0,
            successCount=0,
            failedCount=0
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        logger.info(f"Job created successfully: {job_id} for file: {filename}")
        return job

    @staticmethod
    async def get_job_by_id(db: AsyncSession, job_id: str) -> Optional[Job]:
        result = await db.execute(select(Job).where(Job._id == job_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all_jobs(db: AsyncSession) -> List[Job]:
        result = await db.execute(
            select(Job).order_by(desc(Job.createdAt))
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_last_job(db: AsyncSession) -> Optional[Job]:
        result = await db.execute(
            select(Job).order_by(desc(Job.createdAt)).limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_job_status(
        db: AsyncSession,
        job_id: str,
        status: JobStatus,
        completed_at: Optional[datetime] = None
    ) -> bool:
        logger.debug(f"Updating job {job_id} status to: {status.value}")
        job = await JobService.get_job_by_id(db, job_id)
        if job:
            job.status = status
            if completed_at:
                job.completedAt = completed_at
            await db.commit()
            logger.debug(f"Job {job_id} status updated to: {status.value}")
            return True
        logger.warning(f"Job {job_id} not found, cannot update status")
        return False

    @staticmethod
    async def add_job_error(
        db: AsyncSession,
        job_id: str,
        error_message: str,
        row_number: Optional[int] = None,
        row: Optional[Dict[str, str]] = None
    ) -> JobError:
        error = JobError(
            job_id=job_id,
            error_message=error_message,
            rowNumber=row_number,
            name=((row.get("name") or "").strip() or None) if row else None,
            email=((row.get("email") or "").strip() or None) if row else None,
            phone=((row.get("phone") or "").strip() or None) if row else None,
            company=((row.get("company") or "").strip() or None) if row else None,
        )
        db.add(error)
        await db.commit()
        await db.refresh(error)
        return error

    @staticmethod
    def strip_row_prefix(msg: str) -> str:
        return re.sub(r"^Row\s+\d+:\s*", "", msg or "").strip()

    @staticmethod
    async def get_error_rows(db: AsyncSession, job_id: str) -> List[JobError]:
        result = await db.execute(
            select(JobError)
            .where(JobError.job_id == job_id)
            .where(JobError.rowNumber.is_not(None))
            .order_by(JobError.rowNumber.asc(), JobError.id.asc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_job_errors(db: AsyncSession, job_id: str) -> List[str]:
        result = await db.execute(
            select(JobError.error_message).where(JobError.job_id == job_id)
        )
        return [row[0] for row in result.fetchall()]

    @staticmethod
    async def get_job_errors_batch(
        db: AsyncSession,
        job_ids: List[str]
    ) -> Dict[str, List[str]]:
        if not job_ids:
            return {}
        result = await db.execute(
            select(JobError.job_id, JobError.error_message)
            .where(JobError.job_id.in_(job_ids))
        )
        errors_dict: Dict[str, List[str]] = {job_id: [] for job_id in job_ids}
        for job_id, error_message in result.fetchall():
            errors_dict[job_id].append(error_message)
        return errors_dict

    @staticmethod
    async def update_job_counts(
        db: AsyncSession,
        job_id: str,
        total_rows: Optional[int] = None,
        processed_rows: Optional[int] = None,
        success_count: Optional[int] = None,
        failed_count: Optional[int] = None
    ) -> bool:
        job = await JobService.get_job_by_id(db, job_id)
        if job:
            if total_rows is not None:
                job.totalRows = total_rows
            if processed_rows is not None:
                job.processedRows = processed_rows
            if success_count is not None:
                job.successCount = success_count
            if failed_count is not None:
                job.failedCount = failed_count
            await db.commit()
            return True
        return False

    @staticmethod
    def validate_email(email: str) -> bool:
        if not email or not isinstance(email, str):
            return False
        email = email.strip()
        if not email:
            return False
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    @staticmethod
    def validate_row(row: Dict[str, str], row_number: int) -> Tuple[bool, Optional[str]]:
        errors = []
        name = row.get('name', '').strip() if row.get('name') else ''
        email = row.get('email', '').strip() if row.get('email') else ''
        company = row.get('company', '').strip() if row.get('company') else ''
        if not name:
            errors.append("name is required (cannot be empty)")
        if not email:
            errors.append("email is required (cannot be empty)")
        elif not JobService.validate_email(email):
            errors.append(f"email '{email}' is not a valid email format")
        if not company:
            errors.append("company is required (cannot be empty)")
        if errors:
            error_msg = f"Row {row_number}: {', '.join(errors)}"
            return False, error_msg
        return True, None

    @staticmethod
    async def insert_customer(
        db: AsyncSession,
        job_id: str,
        name: str,
        email: str,
        phone: Optional[str],
        company: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Insert a customer into the database.
        
        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
            - (True, None) on success
            - (False, error_message) on duplicate email (business logic, not an error)
        
        Raises:
            Exception: For database errors other than duplicate email (caller should handle)
        """
        customer_id = str(uuid.uuid4())
        logger.debug(f"Inserting customer {customer_id} for job {job_id}: {email}")
        customer = Customer(
            _id=customer_id,
            name=name,
            email=email,
            phone=phone,
            company=company,
            jobId=job_id
        )
        db.add(customer)
        try:
            await db.commit()
            await db.refresh(customer)
            logger.debug(f"Customer {customer_id} inserted successfully for job {job_id}")
            return True, None
        except IntegrityError as e:
            await db.rollback()
            error_str = str(e).lower()
            if "email" in error_str or "duplicate" in error_str or "unique" in error_str:
                logger.debug(f"Duplicate email detected for job {job_id}: {email}")
                return False, f"email '{email}' must be unique in the database (duplicate found)"
            # Re-raise if it's a different integrity error
            raise

    @staticmethod
    async def process_job_async(file_path: str, job_id: str):
        """
        Process a CSV file asynchronously for a job.
        
        This method processes the file row by row, validates data, inserts customers,
        and publishes progress updates via WebSocket.
        
        Raises:
            FileUploadError: If file is not found
            JobValidationError: If CSV is missing required columns
            Exception: For other processing errors (caller should handle)
        """
        async with AsyncSessionLocal() as db:
            logger.info(f"Starting file processing for job {job_id}, file: {file_path}")
            await JobService.update_job_status(
                db, job_id, JobStatus.PROCESSING
            )
            await job_progress_hub.publish(
                job_id,
                {
                    "type": "status",
                    "jobId": job_id,
                    "status": JobStatus.PROCESSING.value,
                    "ts": datetime.now().isoformat(),
                },
            )
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                raise FileUploadError(f"File not found: {file_path}")
            logger.debug(f"File found: {file_path}, starting CSV parsing")
            processed_rows = 0
            success_count = 0
            failed_count = 0

            total_rows = 0
            required_columns = {'name', 'email', 'phone', 'company'}
            with open(file_path_obj, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                if not required_columns.issubset(set(reader.fieldnames or [])):
                    missing = required_columns - set(reader.fieldnames or [])
                    error_msg = f"CSV file is missing required columns: {', '.join(missing)}"
                    logger.error(f"Job {job_id}: {error_msg}")
                    raise JobValidationError(f"CSV file is missing required columns: {', '.join(missing)}")
                for _ in reader:
                    total_rows += 1

            await JobService.update_job_counts(
                db, job_id,
                total_rows=total_rows,
                processed_rows=0,
                success_count=0,
                failed_count=0
            )
            await job_progress_hub.publish(
                job_id,
                {
                    "type": "progress",
                    "jobId": job_id,
                    "totalRows": total_rows,
                    "processedRows": 0,
                    "successCount": 0,
                    "failedCount": 0,
                    "progress": 0.0,
                    "ts": datetime.now().isoformat(),
                },
            )

            with open(file_path_obj, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                logger.debug(f"CSV columns validated: {reader.fieldnames}")
                for row_number, row in enumerate(reader, start=2):
                    processed_rows += 1
                    is_valid, validation_error = JobService.validate_row(row, row_number)
                    if not is_valid:
                        failed_count += 1
                        await JobService.add_job_error(db, job_id, validation_error, row_number=row_number, row=row)
                        await JobService.update_job_counts(
                            db, job_id,
                            total_rows=total_rows,
                            processed_rows=processed_rows,
                            success_count=success_count,
                            failed_count=failed_count
                        )
                        await job_progress_hub.publish(
                            job_id,
                            {
                                "type": "progress",
                                "jobId": job_id,
                                "rowNumber": row_number,
                                "rowOutcome": "failed",
                                "error": validation_error,
                                "totalRows": total_rows,
                                "processedRows": processed_rows,
                                "successCount": success_count,
                                "failedCount": failed_count,
                                "progress": (processed_rows / total_rows) if total_rows else 0.0,
                                "ts": datetime.now().isoformat(),
                            },
                        )
                        continue
                    name = row['name'].strip()
                    email = row['email'].strip()
                    phone_raw = row.get('phone', '').strip() if row.get('phone') else ''
                    phone = phone_raw if phone_raw else None
                    company = row['company'].strip()
                    success, insert_error = await JobService.insert_customer(
                        db, job_id, name, email, phone, company
                    )
                    if success:
                        success_count += 1
                    else:
                        failed_count += 1
                        error_msg = f"Row {row_number}: {insert_error}"
                        await JobService.add_job_error(db, job_id, error_msg, row_number=row_number, row=row)
                    await JobService.update_job_counts(
                        db, job_id,
                        total_rows=total_rows,
                        processed_rows=processed_rows,
                        success_count=success_count,
                        failed_count=failed_count
                    )
                    await job_progress_hub.publish(
                        job_id,
                        {
                            "type": "progress",
                            "jobId": job_id,
                            "rowNumber": row_number,
                            "rowOutcome": "success" if success else "failed",
                            "error": None if success else insert_error,
                            "totalRows": total_rows,
                            "processedRows": processed_rows,
                            "successCount": success_count,
                            "failedCount": failed_count,
                            "progress": (processed_rows / total_rows) if total_rows else 0.0,
                            "ts": datetime.now().isoformat(),
                        },
                    )
            await JobService.update_job_status(
                db, job_id, JobStatus.COMPLETED, datetime.now()
            )
            await job_progress_hub.publish(
                job_id,
                {
                    "type": "status",
                    "jobId": job_id,
                    "status": JobStatus.COMPLETED.value,
                    "totalRows": total_rows,
                    "processedRows": processed_rows,
                    "successCount": success_count,
                    "failedCount": failed_count,
                    "progress": 1.0 if total_rows else 0.0,
                    "ts": datetime.now().isoformat(),
                },
            )
            logger.info(
                f"File {file_path} processed successfully for job {job_id}. "
                f"Total: {total_rows}, Success: {success_count}, Failed: {failed_count}"
            )

    @staticmethod
    async def delete_all_job_data(db: AsyncSession) -> Dict[str, int]:
        logger.info("Deleting all job-related data from database")
        customers_res = await db.execute(delete(Customer))
        errors_res = await db.execute(delete(JobError))
        jobs_res = await db.execute(delete(Job))
        await db.commit()

        def row_count(res) -> int:
            return int(res.rowcount) if res.rowcount is not None else -1

        deleted_counts = {
            "customers_deleted": row_count(customers_res),
            "job_errors_deleted": row_count(errors_res),
            "jobs_deleted": row_count(jobs_res),
        }
        logger.info(f"Deleted all job data: {deleted_counts}")
        return deleted_counts
