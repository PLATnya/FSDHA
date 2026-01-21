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
            "GET /api/customers": "List all customers"
        }
    }
