from fastapi import FastAPI
import logging

from routers import job_router, root_router, customer_router
from db_session import init_db, close_db
from logging_config import setup_logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Starting application...")
    await init_db()
    logger.info("Application started successfully")
    yield
    logger.info("Shutting down application...")
    await close_db()
    logger.info("Application shut down complete")


app = FastAPI(title="File Upload Service", lifespan=lifespan)

# Include routers
app.include_router(root_router.router)
app.include_router(job_router.router)
app.include_router(customer_router.router)

