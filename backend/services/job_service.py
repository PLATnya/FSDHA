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
        pass

    @staticmethod
    async def get_job_by_id(db: AsyncSession, job_id: str) -> Optional[Job]:
        pass

    @staticmethod
    async def get_all_jobs(db: AsyncSession) -> List[Job]:
        pass

    @staticmethod
    async def get_last_job(db: AsyncSession) -> Optional[Job]:
        pass

    @staticmethod
    async def update_job_status(
        db: AsyncSession,
        job_id: str,
        status: JobStatus,
        completed_at: Optional[datetime] = None
    ) -> bool:
        pass

    @staticmethod
    async def add_job_error(
        db: AsyncSession,
        job_id: str,
        error_message: str
    ) -> JobError:
        pass

    @staticmethod
    async def get_job_errors(db: AsyncSession, job_id: str) -> List[str]:
        pass

    @staticmethod
    async def get_job_errors_batch(
        db: AsyncSession,
        job_ids: List[str]
    ) -> Dict[str, List[str]]:
        pass

    @staticmethod
    async def process_job_async(file_path: str, job_id: str):
        pass
