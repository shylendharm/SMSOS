from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.core.telemetry import get_request_id
from app.core.logging import logger


class AppError(Exception):
    def __init__(self, message: str, code: str = "INTERNAL_SERVER_ERROR", status_code: int = 500, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class NotFoundError(AppError):
    def __init__(self, message: str, code: str = "NOT_FOUND", details: dict | None = None):
        super().__init__(message, code, status.HTTP_404_NOT_FOUND, details)


class ValidationError(AppError):
    def __init__(self, message: str, code: str = "VALIDATION_ERROR", details: dict | None = None):
        super().__init__(message, code, status.HTTP_422_UNPROCESSABLE_ENTITY, details)


class AuthError(AppError):
    def __init__(self, message: str, code: str = "UNAUTHORIZED", details: dict | None = None):
        super().__init__(message, code, status.HTTP_401_UNAUTHORIZED, details)


class ForbiddenError(AppError):
    def __init__(self, message: str, code: str = "FORBIDDEN", details: dict | None = None):
        super().__init__(message, code, status.HTTP_403_FORBIDDEN, details)


class ConflictError(AppError):
    def __init__(self, message: str, code: str = "CONFLICT", details: dict | None = None):
        super().__init__(message, code, status.HTTP_409_CONFLICT, details)


def setup_error_handlers(app: FastAPI):
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        req_id = get_request_id()
        logger.error("app_error", exc_info=exc, code=exc.code, status_code=exc.status_code)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                    "request_id": req_id,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        req_id = get_request_id()
        raw_errors = exc.errors()
        sanitized = []
        for err in raw_errors:
            clean = {}
            for k, v in err.items():
                if isinstance(v, bytes):
                    clean[k] = v.decode("utf-8", errors="replace")
                else:
                    clean[k] = v
            sanitized.append(clean)
        details = {"errors": sanitized}
        logger.warning("validation_error", details=details)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Validation failed",
                    "details": details,
                    "request_id": str(req_id) if req_id else None,
                }
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        req_id = get_request_id()
        logger.exception("unhandled_error", error=str(exc))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred",
                    "details": {},
                    "request_id": req_id,
                }
            },
        )