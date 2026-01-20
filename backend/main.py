from fastapi import FastAPI

from routers import job_router, root_router
from db_session import init_db, close_db

app = FastAPI(title="File Upload Service")

# Include routers
app.include_router(root_router.router)
app.include_router(job_router.router)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    await init_db()


@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown"""
    await close_db()
