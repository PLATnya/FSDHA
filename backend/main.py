from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging

from routers import job_router, root_router, customer_router, ws_router
from db_session import init_db, close_db
from logging_config import setup_logging
from middleware.error_handler import (
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler,
    RequestIDMiddleware
)

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

app.add_middleware(RequestIDMiddleware)

app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Include routers
app.include_router(root_router.router)
app.include_router(job_router.router)
app.include_router(customer_router.router)
app.include_router(ws_router.router)

