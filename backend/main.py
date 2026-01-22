from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
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
from middleware.cors_config import get_allowed_origins

from contextlib import asynccontextmanager

# Set up logger for this module
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Initializes logging and database at startup,
    and properly shuts down resources at shutdown.
    """
    setup_logging()
    logger.info("Starting application...")
    await init_db()
    logger.info("Application started successfully")

    yield
    logger.info("Shutting down application...")
    await close_db()
    logger.info("Application shut down complete")

# Instantiate FastAPI app with custom lifespan handler
app = FastAPI(title="File Upload And Analysis Service", lifespan=lifespan)

# Retrieve allowed origins for CORS policy
allowed_origins = get_allowed_origins()
logger.info(f"CORS allowed origins: {allowed_origins}")

# Add CORS middleware to handle cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Request ID middleware for tracking requests
app.add_middleware(RequestIDMiddleware)

# Register exception handlers for HTTP, validation, and general errors
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Include API routers
app.include_router(root_router.router)
app.include_router(job_router.router)
app.include_router(customer_router.router)
app.include_router(ws_router.router)
