from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import Optional, List, Dict
from datetime import datetime
import uuid

from database import Job, JobError, JobStatus
from db_session import AsyncSessionLocal


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
    async def process_job_async(file_path: str, job_id: str):
        async with AsyncSessionLocal() as db:
            try:
                await JobService.update_job_status(
                    db, job_id, JobStatus.PROCESSING
                )
                import asyncio
                # placeholder for actual file processing
                await asyncio.sleep(3)
                await JobService.update_job_status(
                    db, job_id, JobStatus.COMPLETED, datetime.now()
                )
                print(f"File {file_path} processed successfully for job {job_id}")
            except Exception as e:
                await JobService.update_job_status(
                    db, job_id, JobStatus.FAILED, datetime.now()
                )
                await JobService.add_job_error(db, job_id, str(e))
                print(f"Error processing file for job {job_id}: {e}")
