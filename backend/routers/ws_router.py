from datetime import datetime

from fastapi import APIRouter, WebSocket
from fastapi.websockets import WebSocketDisconnect

from db_session import AsyncSessionLocal
from services.job_service import JobService
from services.job_progress_hub import job_progress_hub
from schemas.validation import validate_job_id


router = APIRouter(tags=["websocket"])


def _iso_now() -> str:
    return datetime.now().isoformat()


@router.websocket("/ws/jobs/{job_id}")
async def job_progress_ws(
    websocket: WebSocket, 
    job_id: str
):
    try:
        validated_job_id = validate_job_id(job_id)
    except ValueError as e:
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

    async with AsyncSessionLocal() as db:
        job = await JobService.get_job_by_id(db, validated_job_id)
        if not job:
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
        pass
    finally:
        await job_progress_hub.unsubscribe(validated_job_id, websocket)

