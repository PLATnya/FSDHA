from fastapi import FastAPI

from routers import job_router, root_router
from db_session import init_db, close_db
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(title="File Upload Service", lifespan=lifespan)

# Include routers
app.include_router(root_router.router)
app.include_router(job_router.router)

