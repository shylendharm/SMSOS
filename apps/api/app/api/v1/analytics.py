from typing import Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_current_user
from app.db.models.user import User
from app.db.models.order import Order
from app.db.models.reservation import Reservation
from app.db.models.inventory import InventoryItem
from app.db.models.customer import Customer

router = APIRouter()


@router.get("/analytics/summary")
async def get_analytics_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    biz_id = current_user.business_id

    # Total orders count
    res_total_orders = await db.execute(select(func.count(Order.id)).where(Order.business_id == biz_id))
    total_orders = res_total_orders.scalar() or 0

    # Pending orders count
    res_pending_orders = await db.execute(
        select(func.count(Order.id)).where(Order.business_id == biz_id, Order.status == "pending")
    )
    pending_orders = res_pending_orders.scalar() or 0

    # Total revenue
    res_revenue = await db.execute(
        select(func.sum(Order.total_amount)).where(Order.business_id == biz_id, Order.status.in_(["ready", "completed", "fulfilled", "delivered"]))
    )
    total_revenue = res_revenue.scalar() or 0.0

    # Total active reservations
    res_reservations = await db.execute(
        select(func.count(Reservation.id)).where(Reservation.business_id == biz_id, Reservation.status == "confirmed")
    )
    total_reservations = res_reservations.scalar() or 0

    # Low stock items count
    res_low_stock = await db.execute(
        select(func.count(InventoryItem.id)).where(InventoryItem.business_id == biz_id, InventoryItem.is_low_stock == True)
    )
    low_stock_count = res_low_stock.scalar() or 0

    # Customers count
    res_customers = await db.execute(select(func.count(Customer.id)).where(Customer.business_id == biz_id))
    total_customers = res_customers.scalar() or 0

    return {
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "new_orders": pending_orders,
        "total_revenue": float(total_revenue),
        "total_reservations": total_reservations,
        "new_reservations": total_reservations,
        "low_stock_items_count": low_stock_count,
        "total_customers": total_customers,
    }


@router.get("/analytics/pending")
async def get_pending_counts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    biz_id = current_user.business_id

    res_pending_orders = await db.execute(
        select(func.count(Order.id)).where(Order.business_id == biz_id, Order.status == "pending")
    )
    new_orders = res_pending_orders.scalar() or 0

    res_pending_res = await db.execute(
        select(func.count(Reservation.id)).where(Reservation.business_id == biz_id, Reservation.status == "confirmed")
    )
    new_reservations = res_pending_res.scalar() or 0

    return {
        "new_orders": new_orders,
        "new_reservations": new_reservations,
    }
