import uuid
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Path
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_current_user
from app.core.errors import NotFoundError, ValidationError
from app.db.models.user import User
from app.db.models.order import Order, OrderItem
from app.db.repositories.order import OrderRepository
from app.db.repositories.customer import CustomerRepository

router = APIRouter()


class OrderItemSchema(BaseModel):
    id: Optional[str] = None
    item_name: str
    quantity: int = Field(gt=0, default=1)
    unit_price: Decimal = Field(ge=0, default=Decimal("0.0"))


class OrderResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    business_id: str
    customer_id: Optional[str] = None
    order_number: int
    status: str
    notes: Optional[str] = None
    total_amount: Optional[Decimal] = None
    created_at: str
    items: List[OrderItemSchema] = []



class CreateOrderItemRequest(BaseModel):
    item_name: str
    quantity: int = Field(gt=0, default=1)
    unit_price: Decimal = Field(ge=0, default=Decimal("0.0"))


class CreateOrderRequest(BaseModel):
    customer_id: Optional[uuid.UUID] = None
    customer_phone: Optional[str] = None
    customer_name: Optional[str] = None
    items: List[CreateOrderItemRequest]
    notes: Optional[str] = None


class UpdateOrderRequest(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


def format_order_response(order: Order) -> dict:
    return {
        "id": str(order.id),
        "business_id": str(order.business_id),
        "customer_id": str(order.customer_id) if order.customer_id else None,
        "order_number": order.order_number,
        "status": order.status,
        "notes": order.notes,
        "total_amount": float(order.total_amount) if order.total_amount is not None else 0.0,
        "created_at": order.created_at.isoformat(),
        "items": [
            {
                "id": str(item.id),
                "item_name": item.item_name,
                "quantity": item.quantity,
                "unit_price": float(item.unit_price),
            }
            for item in getattr(order, "items", [])
        ],
    }


@router.get("/orders", response_model=List[OrderResponse])
async def list_orders(
    status: Optional[str] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = OrderRepository(db)
    orders = await repo.list_by_business(current_user.business_id, status=status, offset=offset, limit=limit)
    return [format_order_response(o) for o in orders]


@router.post("/orders", response_model=OrderResponse, status_code=210)
@router.post("/orders", response_model=OrderResponse)
async def create_order(
    req: CreateOrderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not req.items:
        raise ValidationError("Order must contain at least one item")

    customer_id = req.customer_id
    if not customer_id and req.customer_phone:
        cust_repo = CustomerRepository(db)
        cust = await cust_repo.get_by_phone(req.customer_phone, current_user.business_id)
        if not cust:
            cust = await cust_repo.create(
                business_id=current_user.business_id,
                phone_number=req.customer_phone,
                name=req.customer_name or "Customer",
            )
        customer_id = cust.id

    order_repo = OrderRepository(db)
    next_num = await order_repo.get_next_order_number(current_user.business_id)

    total_amount = sum(item.quantity * item.unit_price for item in req.items)

    order = Order(
        business_id=current_user.business_id,
        customer_id=customer_id,
        order_number=next_num,
        status="pending",
        notes=req.notes,
        total_amount=total_amount,
    )
    db.add(order)
    await db.flush()

    for item_req in req.items:
        item = OrderItem(
            order_id=order.id,
            item_name=item_req.item_name,
            quantity=item_req.quantity,
            unit_price=item_req.unit_price,
        )
        db.add(item)

    await db.commit()
    created_order = await order_repo.get_by_number(next_num, current_user.business_id)
    return format_order_response(created_order or order)


@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: uuid.UUID = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = OrderRepository(db)
    order = await repo.get(order_id)
    if not order or order.business_id != current_user.business_id:
        raise NotFoundError(f"Order with id {order_id} not found")
    # load items
    order_full = await repo.get_by_number(order.order_number, current_user.business_id)
    return format_order_response(order_full or order)


@router.put("/orders/{order_id}", response_model=OrderResponse)
async def update_order(
    req: UpdateOrderRequest,
    order_id: uuid.UUID = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = OrderRepository(db)
    order = await repo.get(order_id)
    if not order or order.business_id != current_user.business_id:
        raise NotFoundError(f"Order with id {order_id} not found")

    if req.status:
        old_status = order.status
        order = await repo.update_status(order_id, req.status, changed_by=current_user.name)
        
        # Trigger outbound notification if status changed
        if order and old_status != req.status and order.customer_id:
            from app.db.repositories.customer import CustomerRepository
            from app.db.models.message import InboundMessage, OutboundMessage
            from app.core.sms import twilio_service
            from sqlalchemy.future import select

            cust_repo = CustomerRepository(db)
            customer = await cust_repo.get(order.customer_id)

            if customer and customer.phone_number:
                # Check if customer communicates via WhatsApp
                res = await db.execute(
                    select(InboundMessage)
                    .where(InboundMessage.from_number == f"whatsapp:{customer.phone_number}")
                    .limit(1)
                )
                is_whatsapp = res.scalars().first() is not None
                to_number = f"whatsapp:{customer.phone_number}" if is_whatsapp else customer.phone_number

                # Determine notification content
                status_msg = f"Your order #{order.order_number} status has been updated to: {req.status.upper()}."
                if req.status.lower() == "ready":
                    status_msg = f"Your order #{order.order_number} is ready for pickup/delivery!"
                elif req.status.lower() == "completed":
                    status_msg = f"Your order #{order.order_number} has been completed. Thank you for your business!"
                elif req.status.lower() == "cancelled":
                    status_msg = f"Your order #{order.order_number} has been cancelled."

                # Send outbound message
                twilio_sid = twilio_service.send_message(to_number=to_number, body=status_msg)
                
                outbound_msg = OutboundMessage(
                    business_id=order.business_id,
                    to_number=to_number,
                    body=status_msg,
                    message_sid=twilio_sid,
                    status="sent" if twilio_sid else "failed",
                )
                db.add(outbound_msg)
                await db.flush()

    if req.notes is not None:
        order.notes = req.notes

    await db.commit()
    order_full = await repo.get_by_number(order.order_number, current_user.business_id)
    return format_order_response(order_full or order)
