from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.core.middleware import setup_middlewares
from app.core.errors import setup_error_handlers
from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("app_startup", env=settings.APP_ENV)
    yield
    logger.info("app_shutdown")


app = FastAPI(
    title="SMSOS API",
    description="SMS-based Operating System for Micro-Businesses Backend API",
    version="0.1.0",
    lifespan=lifespan,
)

setup_error_handlers(app)
setup_middlewares(app)

app.include_router(api_router, prefix="/api/v1")

DASHBOARD_DIR = Path(__file__).resolve().parent.parent.parent / "dashboard"
if DASHBOARD_DIR.exists():
    app.mount("/dashboard", StaticFiles(directory=str(DASHBOARD_DIR), html=True), name="dashboard")

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
async def root_redirect():
    return RedirectResponse(url="/dashboard")

if __name__ == "__main__":
    import uvicorn
    from urllib.parse import urlparse
    
    port = 8000
    try:
        url_parts = urlparse(settings.API_BASE_URL)
        if url_parts.port:
            port = url_parts.port
    except Exception:
        pass
        
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)