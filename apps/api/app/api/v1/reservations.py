import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Path
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_current_user
from app.core.errors import NotFoundError, ConflictError
from app.db.models.user import User
from app.db.models.reservation import Reservation
from app.db.repositories.reservation import ReservationRepository
from app.db.repositories.customer import CustomerRepository

router = APIRouter()


class ReservationResponse(BaseModel):
    id: str
    business_id: str
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    reserved_at: str
    duration_minutes: int
    table_or_slot: Optional[str] = None
    party_size: int
    status: str
    notes: Optional[str] = None
    created_at: str


class CreateReservationRequest(BaseModel):
    customer_name: str
    customer_phone: Optional[str] = None
    reserved_at: datetime
    duration_minutes: int = Field(gt=0, default=60)
    party_size: int = Field(gt=0, default=1)
    table_or_slot: Optional[str] = None
    notes: Optional[str] = None


class UpdateReservationRequest(BaseModel):
    status: Optional[str] = None
    reserved_at: Optional[datetime] = None
    party_size: Optional[int] = None
    table_or_slot: Optional[str] = None
    notes: Optional[str] = None


def format_reservation_response(res: Reservation) -> dict:
    return {
        "id": str(res.id),
        "business_id": str(res.business_id),
        "customer_id": str(res.customer_id) if res.customer_id else None,
        "customer_name": res.customer_name,
        "reserved_at": res.reserved_at.isoformat(),
        "duration_minutes": res.duration_minutes,
        "table_or_slot": res.table_or_slot,
        "party_size": res.party_size,
        "status": res.status,
        "notes": res.notes,
        "created_at": res.created_at.isoformat(),
    }


@router.get("/reservations/availability")
async def get_availability(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format, defaults to today"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime as dt_cls, timezone as tz_cls
    from app.modules.reservation_service import get_day_occupancy_matrix, get_business_settings, check_table_availability

    settings = await get_business_settings(db, current_user.business_id)
    total_tables = (settings.table_count if settings and settings.table_count else 10)
    slot_duration = (settings.reservation_slot_duration if settings else 90) or 90
    opening_time = (settings.opening_time if settings else "10:00") or "10:00"
    closing_time = (settings.closing_time if settings else "22:00") or "22:00"

    if date:
        try:
            target_date = dt_cls.fromisoformat(date).replace(tzinfo=tz_cls.utc)
        except ValueError:
            target_date = dt_cls.now(tz_cls.utc)
    else:
        target_date = dt_cls.now(tz_cls.utc)

    matrix = await get_day_occupancy_matrix(db, current_user.business_id, target_date, slot_duration)

    # Build per-table status for the Visual Table Grid (deduplicated per reservation)
    repo = ReservationRepository(db)
    day_reservations = await repo.list_by_business(current_user.business_id, date=target_date)

    all_table_names = [f"Table {i}" for i in range(1, total_tables + 1)]
    table_grid = []
    for tname in all_table_names:
        bookings = []
        for r in day_reservations:
            if r.status in ["confirmed", "seated"] and r.table_or_slot:
                assigned_tables = [t.strip() for t in r.table_or_slot.split(",")]
                if tname in assigned_tables:
                    try:
                        time_str = r.reserved_at.strftime("%I:%M %p").lstrip("0")
                    except Exception:
                        time_str = r.reserved_at.strftime("%H:%M")
                    bookings.append({
                        "id": str(r.id),
                        "customer": r.customer_name or "Guest",
                        "party_size": r.party_size,
                        "time": time_str,
                        "duration": r.duration_minutes,
                    })
        table_grid.append({
            "table_name": tname,
            "status": "reserved" if bookings else "available",
            "bookings": bookings,
        })

    return {
        "date": target_date.strftime("%Y-%m-%d"),
        "total_tables": total_tables,
        "slot_duration": slot_duration,
        "opening_time": opening_time,
        "closing_time": closing_time,
        "hourly_matrix": matrix,
        "table_grid": table_grid,
    }


@router.get("/reservations", response_model=List[ReservationResponse])
async def list_reservations(
    date: Optional[datetime] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = ReservationRepository(db)
    items = await repo.list_by_business(current_user.business_id, date=date, offset=offset, limit=limit)
    return [format_reservation_response(r) for r in items]


@router.post("/reservations", response_model=ReservationResponse)
async def create_reservation(
    req: CreateReservationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.modules.reservation_service import allocate_table_number, get_business_settings

    settings = await get_business_settings(db, current_user.business_id)
    slot_duration = (settings.reservation_slot_duration if settings else 90) or req.duration_minutes

    # Auto-allocate table if not manually specified
    table_name = req.table_or_slot
    if not table_name:
        table_name = await allocate_table_number(db, current_user.business_id, req.reserved_at, slot_duration, party_size=req.party_size)
        if table_name is None:
            raise ConflictError(
                f"Not enough free tables for a party of {req.party_size} at this time slot. "
                f"Please choose a different time or reduce party size."
            )
    else:
        # Validate manual table assignment against conflicts
        repo = ReservationRepository(db)
        conflict = await repo.check_conflict(
            business_id=current_user.business_id,
            table_or_slot=table_name,
            reserved_at=req.reserved_at,
        )
        if conflict:
            raise ConflictError(f"Table '{table_name}' is already reserved for this time slot")

    customer_id = None
    if req.customer_phone:
        cust_repo = CustomerRepository(db)
        cust = await cust_repo.get_by_phone(req.customer_phone, current_user.business_id)
        if not cust:
            cust = await cust_repo.create(
                business_id=current_user.business_id,
                phone_number=req.customer_phone,
                name=req.customer_name,
            )
        customer_id = cust.id

    reservation = Reservation(
        business_id=current_user.business_id,
        customer_id=customer_id,
        customer_name=req.customer_name,
        reserved_at=req.reserved_at,
        duration_minutes=slot_duration,
        table_or_slot=table_name,
        party_size=req.party_size,
        status="confirmed",
        notes=req.notes,
    )
    db.add(reservation)
    await db.commit()
    await db.refresh(reservation)
    return format_reservation_response(reservation)


@router.patch("/reservations/{reservation_id}", response_model=ReservationResponse)
async def update_reservation(
    req: UpdateReservationRequest,
    reservation_id: uuid.UUID = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = ReservationRepository(db)
    res = await repo.get(reservation_id)
    if not res or res.business_id != current_user.business_id:
        raise NotFoundError(f"Reservation with id {reservation_id} not found")

    new_table = req.table_or_slot or res.table_or_slot
    new_time = req.reserved_at or res.reserved_at

    if new_table and (req.table_or_slot or req.reserved_at):
        conflict = await repo.check_conflict(
            business_id=current_user.business_id,
            table_or_slot=new_table,
            reserved_at=new_time,
            exclude_id=reservation_id,
        )
        if conflict:
            raise ConflictError(f"Table/slot '{new_table}' is already reserved for this time slot")

    if req.status is not None:
        res.status = req.status
    if req.reserved_at is not None:
        res.reserved_at = req.reserved_at
    if req.table_or_slot is not None:
        res.table_or_slot = req.table_or_slot
    if req.party_size is not None:
        res.party_size = req.party_size
    if req.notes is not None:
        res.notes = req.notes

    await db.commit()
    await db.refresh(res)
    return format_reservation_response(res)


@router.delete("/reservations/{reservation_id}")
async def delete_reservation(
    reservation_id: uuid.UUID = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = ReservationRepository(db)
    res = await repo.get(reservation_id)
    if not res or res.business_id != current_user.business_id:
        raise NotFoundError(f"Reservation with id {reservation_id} not found")
    await repo.delete(reservation_id)
    return {"status": "success", "message": "Reservation deleted successfully"}
