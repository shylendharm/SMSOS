from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_current_user
from app.db.models.user import User
from app.db.models.message import InboundMessage, OutboundMessage
from app.db.models.customer import Customer

router = APIRouter()


@router.get("/conversations")
async def list_conversations(
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    biz_id = current_user.business_id

    # Fetch recent inbound messages
    res_inbound = await db.execute(
        select(InboundMessage)
        .where(InboundMessage.business_id == biz_id)
        .order_by(InboundMessage.created_at.desc())
        .limit(limit)
    )
    inbound_msgs = list(res_inbound.scalars().all())

    # Fetch recent outbound messages
    res_outbound = await db.execute(
        select(OutboundMessage)
        .where(OutboundMessage.business_id == biz_id)
        .order_by(OutboundMessage.created_at.desc())
        .limit(limit)
    )
    outbound_msgs = list(res_outbound.scalars().all())

    # Fetch customers map
    res_customers = await db.execute(select(Customer).where(Customer.business_id == biz_id))
    customers = {c.phone_number: c.name for c in res_customers.scalars().all()}

    # Merge and group by phone number
    threads: Dict[str, Dict[str, Any]] = {}

    for msg in inbound_msgs:
        phone = msg.from_number
        if phone not in threads:
            threads[phone] = {
                "phone_number": phone,
                "customer_name": customers.get(phone) or "Customer",
                "last_message": msg.body,
                "last_updated": msg.created_at.isoformat(),
                "messages": [],
            }
        threads[phone]["messages"].append({
            "id": str(msg.id),
            "direction": "inbound",
            "from_number": msg.from_number,
            "to_number": msg.to_number,
            "body": msg.body,
            "timestamp": msg.created_at.isoformat(),
        })

    for msg in outbound_msgs:
        phone = msg.to_number
        if phone not in threads:
            threads[phone] = {
                "phone_number": phone,
                "customer_name": customers.get(phone) or "Customer",
                "last_message": msg.body,
                "last_updated": msg.created_at.isoformat(),
                "messages": [],
            }
        threads[phone]["messages"].append({
            "id": str(msg.id),
            "direction": "outbound",
            "from_number": "Business",
            "to_number": msg.to_number,
            "body": msg.body,
            "status": msg.status,
            "timestamp": msg.created_at.isoformat(),
        })

    # Sort threads by last message timestamp
    result_list = list(threads.values())
    for t in result_list:
        t["messages"].sort(key=lambda m: m["timestamp"])
    result_list.sort(key=lambda t: t["last_updated"], reverse=True)

    return result_list
