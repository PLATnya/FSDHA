from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.exc import IntegrityError
from typing import Optional, List, Dict, Tuple
from datetime import datetime
import uuid
import csv
import re
from pathlib import Path
import logging

from database import Job, JobError, JobStatus, Customer
from db_session import AsyncSessionLocal

logger = logging.getLogger(__name__)

class JobService:
    @staticmethod
    async def create_job(
        db: AsyncSession,
        filename: str
    ) -> Job:
        job_id = str(uuid.uuid4())
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
        job = await JobService.get_job_by_id(db, job_id)
        if job:
            job.status = status
            if completed_at:
                job.completedAt = completed_at
            await db.commit()
            return True
        return False

    @staticmethod
    async def add_job_error(
        db: AsyncSession,
        job_id: str,
        error_message: str
    ) -> JobError:
        error = JobError(job_id=job_id, error_message=error_message)
        db.add(error)
        await db.commit()
        await db.refresh(error)
        return error

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
        try:
            customer_id = str(uuid.uuid4())
            customer = Customer(
                _id=customer_id,
                name=name,
                email=email,
                phone=phone,
                company=company,
                jobId=job_id
            )
            db.add(customer)
            await db.commit()
            await db.refresh(customer)
            return True, None
        except IntegrityError as e:
            await db.rollback()
            error_str = str(e).lower()
            if "email" in error_str or "duplicate" in error_str or "unique" in error_str:
                return False, f"email '{email}' must be unique in the database (duplicate found)"
            return False, f"Database integrity error: {str(e)}"
        except Exception as e:
            await db.rollback()
            return False, f"Error inserting customer: {str(e)}"

    @staticmethod
    async def process_job_async(file_path: str, job_id: str):
        async with AsyncSessionLocal() as db:
            try:
                logger.info(f"Starting file processing for job {job_id}, file: {file_path}")
                await JobService.update_job_status(
                    db, job_id, JobStatus.PROCESSING
                )
                file_path_obj = Path(file_path)
                if not file_path_obj.exists():
                    raise FileNotFoundError(f"File not found: {file_path}")
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
                        raise ValueError(error_msg)
                    for _ in reader:
                        total_rows += 1

                await JobService.update_job_counts(
                    db, job_id,
                    total_rows=total_rows,
                    processed_rows=0,
                    success_count=0,
                    failed_count=0
                )

                with open(file_path_obj, 'r', encoding='utf-8') as csvfile:
                    reader = csv.DictReader(csvfile)
                    logger.debug(f"CSV columns validated: {reader.fieldnames}")
                    for row_number, row in enumerate(reader, start=2):
                        processed_rows += 1
                        is_valid, validation_error = JobService.validate_row(row, row_number)
                        if not is_valid:
                            failed_count += 1
                            await JobService.add_job_error(db, job_id, validation_error)
                            await JobService.update_job_counts(
                                db, job_id,
                                total_rows=total_rows,
                                processed_rows=processed_rows,
                                success_count=success_count,
                                failed_count=failed_count
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
                            await JobService.add_job_error(db, job_id, error_msg)
                        await JobService.update_job_counts(
                            db, job_id,
                            total_rows=total_rows,
                            processed_rows=processed_rows,
                            success_count=success_count,
                            failed_count=failed_count
                        )
                await JobService.update_job_status(
                    db, job_id, JobStatus.COMPLETED, datetime.now()
                )
                logger.info(
                    f"File {file_path} processed successfully for job {job_id}. "
                    f"Total: {total_rows}, Success: {success_count}, Failed: {failed_count}"
                )
            except Exception as e:
                await JobService.update_job_status(
                    db, job_id, JobStatus.FAILED, datetime.now()
                )
                await JobService.add_job_error(db, job_id, str(e))
                logger.error(f"Error processing file for job {job_id}: {e}", exc_info=True)
