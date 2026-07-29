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


@router.get("/analytics/trends")
async def get_analytics_trends(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    from datetime import datetime as dt_cls, timedelta, timezone as tz_cls
    from app.db.models.order import OrderItem

    biz_id = current_user.business_id
    now = dt_cls.now(tz_cls.utc)
    seven_days_ago = now - timedelta(days=6)
    start_of_period = seven_days_ago.replace(hour=0, minute=0, second=0, microsecond=0)

    # Daily revenue and order counts for last 7 days
    daily_stats = []
    for i in range(7):
        day_start = start_of_period + timedelta(days=i)
        day_end = day_start + timedelta(days=1)

        res_count = await db.execute(
            select(func.count(Order.id)).where(
                Order.business_id == biz_id,
                Order.created_at >= day_start,
                Order.created_at < day_end,
            )
        )
        day_count = res_count.scalar() or 0

        res_rev = await db.execute(
            select(func.sum(Order.total_amount)).where(
                Order.business_id == biz_id,
                Order.created_at >= day_start,
                Order.created_at < day_end,
                Order.status.in_(["confirmed", "ready", "completed", "fulfilled", "delivered"]),
            )
        )
        day_revenue = float(res_rev.scalar() or 0)

        daily_stats.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "label": day_start.strftime("%a"),
            "orders": day_count,
            "revenue": day_revenue,
        })

    # Top 5 selling items by total quantity
    res_top = await db.execute(
        select(
            OrderItem.item_name,
            func.sum(OrderItem.quantity).label("total_qty"),
        )
        .join(Order, OrderItem.order_id == Order.id)
        .where(Order.business_id == biz_id)
        .group_by(OrderItem.item_name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(5)
    )
    top_items = [{"item_name": row[0], "total_quantity": int(row[1])} for row in res_top.all()]

    # Order status breakdown
    res_status = await db.execute(
        select(
            Order.status,
            func.count(Order.id).label("count"),
        )
        .where(Order.business_id == biz_id)
        .group_by(Order.status)
    )
    status_breakdown = {row[0]: int(row[1]) for row in res_status.all()}

    return {
        "daily_stats": daily_stats,
        "top_items": top_items,
        "status_breakdown": status_breakdown,
    }
