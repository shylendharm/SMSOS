from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.db.repositories.base import BaseRepository
from app.db.models.order import Order, OrderItem, OrderStatusHistory
import uuid


class OrderRepository(BaseRepository[Order]):
    def __init__(self, db):
        super().__init__(Order, db)

    async def get_by_number(self, order_number: int, business_id: uuid.UUID) -> Order | None:
        result = await self.db.execute(
            select(Order)
            .where(Order.business_id == business_id, Order.order_number == order_number)
            .options(selectinload(Order.items))
        )
        return result.scalars().first()

    async def get_next_order_number(self, business_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(Order.order_number)
            .where(Order.business_id == business_id)
            .order_by(Order.order_number.desc())
            .limit(1)
        )
        last = result.scalar()
        return (last or 0) + 1

    async def list_by_business(self, business_id: uuid.UUID, status: str | None = None, offset: int = 0, limit: int = 50) -> list[Order]:
        q = select(Order).where(Order.business_id == business_id).options(selectinload(Order.items))
        if status and status != "all":
            q = q.where(Order.status == status)
        elif status != "all":
            # By default, exclude unconfirmed draft orders from kitchen dashboard
            q = q.where(Order.status.notin_(["draft", "pending_confirmation"]))
        q = q.order_by(Order.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def update_status(self, order_id: uuid.UUID, new_status: str, changed_by: str = "system") -> Order | None:
        order = await self.get(order_id)
        if not order:
            return None
        old_status = order.status
        order.status = new_status
        history = OrderStatusHistory(order_id=order.id, from_status=old_status, to_status=new_status, changed_by=changed_by)
        self.db.add(history)
        await self.db.flush()
        return order