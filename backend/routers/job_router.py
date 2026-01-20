from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db_session import get_db

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("")
async def list_jobs(db: AsyncSession = Depends(get_db)):
    pass

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    pass

@router.get("/id")
async def get_last_id(db: AsyncSession = Depends(get_db)):
    """Return the last job ID from the queue of async tasks"""
    pass
