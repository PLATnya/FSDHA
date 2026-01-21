from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Any

logger = logging.getLogger(__name__)



class RequestIDMiddleware(BaseHTTPMiddleware):    
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        
        return response


def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    request_id = get_request_id(request)
    
    # Log 4xx as warning, 5xx as error
    if exc.status_code >= 500:
        logger.error(
            f"HTTP {exc.status_code} error on {request.method} {request.url.path}: {exc.detail}",
            exc_info=False,
            extra={
                "status_code": exc.status_code,
                "path": request.url.path,
                "method": request.method,
                "request_id": request_id,
                "exception_type": type(exc).__name__,
            }
        )
    else:
        logger.warning(
            f"HTTP {exc.status_code} error on {request.method} {request.url.path}: {exc.detail}",
            extra={
                "status_code": exc.status_code,
                "path": request.url.path,
                "method": request.method,
                "request_id": request_id,
                "exception_type": type(exc).__name__,
            }
        )
    
    response = JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": "HTTPException",
                "status_code": exc.status_code,
                "detail": exc.detail,
                "path": request.url.path,
                "method": request.method,
                "request_id": request_id,
            }
        }
    )
    response.headers["X-Request-ID"] = request_id
    return response


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    request_id = get_request_id(request)
    errors = exc.errors()
    logger.warning(
        f"Validation error on {request.method} {request.url.path}: {errors}",
        extra={"path": request.url.path, "request_id": request_id}
    )
    
    response = JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "type": "ValidationError",
                "status_code": 422,
                "detail": "Request validation failed",
                "errors": errors,
                "path": request.url.path,
                "method": request.method,
                "request_id": request_id,
            }
        }
    )
    response.headers["X-Request-ID"] = request_id
    return response


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = get_request_id(request)
    logger.error(
        f"Unhandled exception on {request.method} {request.url.path}: {type(exc).__name__}: {str(exc)}",
        exc_info=True,
        extra={
            "path": request.url.path,
            "method": request.method,
            "request_id": request_id,
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
        }
    )
    
    detail = str(exc) if logger.level <= logging.DEBUG else "An internal server error occurred"
    
    response = JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "type": "InternalServerError",
                "status_code": 500,
                "detail": detail,
                "path": request.url.path,
                "method": request.method,
                "request_id": request_id,
            }
        }
    )
    response.headers["X-Request-ID"] = request_id
    return response
