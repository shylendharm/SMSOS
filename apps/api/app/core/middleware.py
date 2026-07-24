import time
import sys
import uuid
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.telemetry import set_request_id, set_correlation_id, clear_telemetry_context
from app.core.logging import logger
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings


class TelemetryMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        set_request_id(request_id)
        set_correlation_id(correlation_id)
        start_time = time.perf_counter()
        logger.info("request_started", method=request.method, path=request.url.path)
        try:
            response = await call_next(request)
            process_time = time.perf_counter() - start_time
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time:.4f}s"
            logger.info(
                "request_finished",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration=f"{process_time:.4f}s",
            )
            return response
        except Exception as e:
            process_time = time.perf_counter() - start_time
            logger.exception("request_failed", method=request.method, path=request.url.path, duration=f"{process_time:.4f}s", error=str(e))
            raise
        finally:
            clear_telemetry_context()


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}

    async def dispatch(self, request: Request, call_next):
        if "pytest" in sys.modules or settings.APP_ENV == "testing":
            return await call_next(request)
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        timestamps = self.requests.get(client_ip, [])
        timestamps = [t for t in timestamps if now - t < self.window_seconds]
        if len(timestamps) >= self.max_requests:
            from fastapi.responses import JSONResponse
            logger.warning("rate_limit_exceeded", client_ip=client_ip)
            return JSONResponse(
                status_code=429,
                content={"error": {"code": "RATE_LIMIT_EXCEEDED", "message": "Too many requests. Please try again later."}},
            )
        timestamps.append(now)
        self.requests[client_ip] = timestamps
        return await call_next(request)


def setup_middlewares(app: FastAPI):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.APP_ENV == "development" else [settings.FRONTEND_BASE_URL],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RateLimitMiddleware, max_requests=120, window_seconds=60)
    app.add_middleware(TelemetryMiddleware)