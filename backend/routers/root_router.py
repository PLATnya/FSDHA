from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def root():
    return {
        "message": "File Upload Service API",
        "endpoints": {
            "GET /api/jobs": "List all jobs",
            "POST /api/jobs/upload": "Upload a file and get a job ID",
            "GET /api/jobs/{job_id}": "Get job status and progress",
            "GET /api/jobs/id": "Get the last job ID from the queue",
            "DELETE /api/jobs/reset": "Cancel ongoing jobs and delete all job-related data",
            "GET /api/customers": "List all customers",
            "WS /ws/jobs/{job_id}": "Subscribe to per-row job progress events"
        }
    }
