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
    repo = ReservationRepository(db)

    if req.table_or_slot:
        conflict = await repo.check_conflict(
            business_id=current_user.business_id,
            table_or_slot=req.table_or_slot,
            reserved_at=req.reserved_at,
        )
        if conflict:
            raise ConflictError(f"Table/slot '{req.table_or_slot}' is already reserved for this time slot")

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
        duration_minutes=req.duration_minutes,
        table_or_slot=req.table_or_slot,
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
