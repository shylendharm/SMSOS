from fastapi import APIRouter
from app.core.logging import logger

router = APIRouter()


@router.get("/health")
async def health_check():
    logger.info("health_check")
    return {
        "status": "ok",
        "service": "smsos-api",
        "version": "0.1.0",
    }