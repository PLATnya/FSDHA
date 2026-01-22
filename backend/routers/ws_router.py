from datetime import datetime
import logging

from fastapi import APIRouter, WebSocket
from fastapi.websockets import WebSocketDisconnect

from db_session import AsyncSessionLocal
from services.job_service import JobService
from services.job_progress_hub import job_progress_hub
from schemas.validation import validate_job_id

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


def _iso_now() -> str:
    return datetime.now().isoformat()


@router.websocket("/ws/jobs/{job_id}")
async def job_progress_ws(
    websocket: WebSocket, 
    job_id: str
):
    logger.info(f"WebSocket connection attempt for job: {job_id}", extra={"job_id": job_id})
    
    try:
        validated_job_id = validate_job_id(job_id)
    except ValueError as e:
        logger.warning(f"Invalid job_id format in WebSocket: {job_id} - {str(e)}", extra={"job_id": job_id})
        await websocket.accept()
        await websocket.send_json(
            {
                "type": "error",
                "jobId": job_id,
                "message": str(e),
                "ts": _iso_now(),
            }
        )
        await websocket.close(code=1008, reason=str(e))
        return
    
    await websocket.accept()
    logger.debug(f"WebSocket connection accepted for job: {validated_job_id}", extra={"job_id": validated_job_id})

    async with AsyncSessionLocal() as db:
        job = await JobService.get_job_by_id(db, validated_job_id)
        if not job:
            logger.warning(f"Job not found for WebSocket connection: {validated_job_id}", extra={"job_id": validated_job_id})
            await websocket.send_json(
                {
                    "type": "error",
                    "jobId": validated_job_id,
                    "message": "Job not found",
                    "ts": _iso_now(),
                }
            )
            await websocket.close(code=1008)
            return

        logger.info(f"WebSocket connected for job: {validated_job_id}, status: {job.status.value}", extra={"job_id": validated_job_id, "status": job.status.value})
        await websocket.send_json(
            {
                "type": "snapshot",
                "jobId": job._id,
                "filename": job.filename,
                "status": job.status.value,
                "totalRows": job.totalRows,
                "processedRows": job.processedRows,
                "successCount": job.successCount,
                "failedCount": job.failedCount,
                "createdAt": job.createdAt.isoformat() if job.createdAt else None,
                "completedAt": job.completedAt.isoformat() if job.completedAt else None,
                "ts": _iso_now(),
            }
        )

    await job_progress_hub.subscribe(validated_job_id, websocket)

    try:
        while True:
            await websocket.receive()
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for job: {validated_job_id}", extra={"job_id": validated_job_id})
    finally:
        await job_progress_hub.unsubscribe(validated_job_id, websocket)
        logger.debug(f"WebSocket unsubscribed for job: {validated_job_id}", extra={"job_id": validated_job_id})

