import uuid
from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.dependencies import get_db, get_current_user
from app.db.models.user import User
from app.db.models.business import BusinessSettings

router = APIRouter()


class BusinessSettingsResponse(BaseModel):
    table_count: int = 10
    reservation_slot_duration: int = 90
    opening_time: str = "10:00"
    closing_time: str = "22:00"
    operating_hours: dict = {}


class UpdateBusinessSettingsRequest(BaseModel):
    table_count: Optional[int] = Field(None, ge=1, le=500)
    reservation_slot_duration: Optional[int] = Field(None, ge=15, le=300)
    opening_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    closing_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")


@router.get("/business/settings", response_model=BusinessSettingsResponse)
async def get_business_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(BusinessSettings).where(BusinessSettings.business_id == current_user.business_id)
    )
    settings = res.scalars().first()
    if not settings:
        settings = BusinessSettings(
            business_id=current_user.business_id,
            table_count=10,
        )
        db.add(settings)
        await db.commit()
        await db.refresh(settings)

    return {
        "table_count": settings.table_count if settings.table_count is not None else 10,
        "reservation_slot_duration": settings.reservation_slot_duration or 90,
        "opening_time": settings.opening_time or "10:00",
        "closing_time": settings.closing_time or "22:00",
        "operating_hours": settings.operating_hours or {},
    }


@router.put("/business/settings", response_model=BusinessSettingsResponse)
async def update_business_settings(
    req: UpdateBusinessSettingsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(BusinessSettings).where(BusinessSettings.business_id == current_user.business_id)
    )
    settings = res.scalars().first()
    if not settings:
        settings = BusinessSettings(
            business_id=current_user.business_id,
            table_count=req.table_count if req.table_count is not None else 10,
        )
        db.add(settings)
    else:
        if req.table_count is not None:
            settings.table_count = req.table_count
    if req.reservation_slot_duration is not None:
        settings.reservation_slot_duration = req.reservation_slot_duration
    if req.opening_time is not None:
        settings.opening_time = req.opening_time
    if req.closing_time is not None:
        settings.closing_time = req.closing_time

    await db.commit()
    await db.refresh(settings)

    return {
        "table_count": settings.table_count if settings.table_count is not None else 10,
        "reservation_slot_duration": settings.reservation_slot_duration or 90,
        "opening_time": settings.opening_time or "10:00",
        "closing_time": settings.closing_time or "22:00",
        "operating_hours": settings.operating_hours or {},
    }
