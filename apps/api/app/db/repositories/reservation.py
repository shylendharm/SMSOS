from datetime import datetime, timezone
from sqlalchemy.future import select
from app.db.repositories.base import BaseRepository
from app.db.models.reservation import Reservation
import uuid


class ReservationRepository(BaseRepository[Reservation]):
    def __init__(self, db):
        super().__init__(Reservation, db)

    async def list_by_business(self, business_id: uuid.UUID, date: datetime | None = None, offset: int = 0, limit: int = 50) -> list[Reservation]:
        q = select(Reservation).where(Reservation.business_id == business_id)
        if date:
            day_start = datetime(date.year, date.month, date.day, tzinfo=timezone.utc)
            day_end = day_start.replace(hour=23, minute=59, second=59)
            q = q.where(Reservation.reserved_at >= day_start, Reservation.reserved_at <= day_end)
        q = q.order_by(Reservation.reserved_at.asc()).offset(offset).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def check_conflict(self, business_id: uuid.UUID, table_or_slot: str, reserved_at: datetime, exclude_id: uuid.UUID | None = None) -> Reservation | None:
        q = select(Reservation).where(
            Reservation.business_id == business_id,
            Reservation.table_or_slot == table_or_slot,
            Reservation.reserved_at == reserved_at,
            Reservation.status != "cancelled",
        )
        if exclude_id:
            q = q.where(Reservation.id != exclude_id)
        result = await self.db.execute(q)
        return result.scalars().first()

    async def cancel_by_name(self, customer_name: str, business_id: uuid.UUID) -> Reservation | None:
        result = await self.db.execute(
            select(Reservation).where(
                Reservation.business_id == business_id,
                Reservation.customer_name.ilike(customer_name),
                Reservation.status == "confirmed",
            ).order_by(Reservation.reserved_at.desc()).limit(1)
        )
        res = result.scalars().first()
        if res:
            res.status = "cancelled"
            await self.db.flush()
        return res