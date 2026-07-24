import uuid
from decimal import Decimal
from datetime import datetime, timezone
import pytest
from sqlalchemy import select
from app.db.models import (
    Business,
    BusinessSettings,
    User,
    Customer,
    InboundMessage,
    OutboundMessage,
    Order,
    OrderItem,
    Reservation,
    InventoryItem,
    InventoryThreshold,
    CatalogItem,
    WebhookEvent,
    IntentPrediction,
    ConversationState,
)


@pytest.mark.asyncio
async def test_all_14_models_creation(db_session):
    # 1. Business
    biz = Business(
        name="Test Business",
        business_type="restaurant",
        phone_number=f"+1555{uuid.uuid4().hex[:7]}",
        timezone="UTC",
        is_active=True,
    )
    db_session.add(biz)
    await db_session.flush()

    assert biz.id is not None
    assert biz.name == "Test Business"

    # 2. BusinessSettings
    settings = BusinessSettings(
        business_id=biz.id,
        operating_hours={"mon": "09:00-17:00"},
        table_count=10,
    )
    db_session.add(settings)
    await db_session.flush()

    assert settings.business_id == biz.id
    assert settings.table_count == 10

    # 3. User
    user = User(
        business_id=biz.id,
        email=f"test_{uuid.uuid4().hex[:6]}@example.com",
        hashed_password="hashed_pass_value",
        name="Test Owner",
        role="owner",
    )
    db_session.add(user)
    await db_session.flush()

    assert user.id is not None
    assert user.role == "owner"

    # 4. Customer
    customer = Customer(
        business_id=biz.id,
        phone_number="+1234567890",
        name="John Doe",
    )
    db_session.add(customer)
    await db_session.flush()

    assert customer.id is not None
    assert customer.phone_number == "+1234567890"

    # 5. InboundMessage
    inbound = InboundMessage(
        business_id=biz.id,
        message_sid=f"SM{uuid.uuid4().hex}",
        from_number="+1234567890",
        to_number=biz.phone_number,
        body="Hello world",
        processed=False,
    )
    db_session.add(inbound)
    await db_session.flush()

    assert inbound.id is not None
    assert inbound.body == "Hello world"

    # 6. OutboundMessage
    outbound = OutboundMessage(
        business_id=biz.id,
        to_number="+1234567890",
        body="Order confirmed",
        status="sent",
        message_sid=f"SM{uuid.uuid4().hex}",
    )
    db_session.add(outbound)
    await db_session.flush()

    assert outbound.id is not None
    assert outbound.status == "sent"

    # 7. Order
    order = Order(
        business_id=biz.id,
        customer_id=customer.id,
        order_number=101,
        status="pending",
        total_amount=Decimal("150.00"),
    )
    db_session.add(order)
    await db_session.flush()

    assert order.id is not None
    assert order.order_number == 101

    # 8. OrderItem
    order_item = OrderItem(
        order_id=order.id,
        item_name="Espresso",
        quantity=2,
        unit_price=Decimal("75.00"),
    )
    db_session.add(order_item)
    await db_session.flush()

    assert order_item.id is not None
    assert order_item.quantity == 2

    # 9. Reservation
    reservation = Reservation(
        business_id=biz.id,
        customer_id=customer.id,
        customer_name="John Doe",
        reserved_at=datetime.now(timezone.utc),
        party_size=4,
        table_or_slot="Table 5",
        status="confirmed",
    )
    db_session.add(reservation)
    await db_session.flush()

    assert reservation.id is not None
    assert reservation.party_size == 4

    # 10. InventoryItem
    inv_item = InventoryItem(
        business_id=biz.id,
        item_name="Coffee Beans",
        current_quantity=Decimal("15.5"),
        unit="kg",
        is_low_stock=False,
    )
    db_session.add(inv_item)
    await db_session.flush()

    assert inv_item.id is not None

    # 11. InventoryThreshold
    threshold = InventoryThreshold(
        item_id=inv_item.id,
        low_threshold=Decimal("5.0"),
        reorder_quantity=Decimal("20.0"),
    )
    db_session.add(threshold)
    await db_session.flush()

    assert threshold.item_id == inv_item.id

    # 12. CatalogItem
    cat_item = CatalogItem(
        business_id=biz.id,
        name="Cappuccino",
        price=Decimal("120.00"),
        unit="cup",
        category="Beverages",
        is_available=True,
    )
    db_session.add(cat_item)
    await db_session.flush()

    assert cat_item.id is not None
    assert cat_item.name == "Cappuccino"

    # 13. WebhookEvent
    webhook = WebhookEvent(
        event_id=f"evt_{uuid.uuid4().hex}",
        event_type="twilio.inbound",
        payload={"From": "+1234567890"},
        processed=True,
    )
    db_session.add(webhook)
    await db_session.flush()

    assert webhook.id is not None
    assert webhook.processed is True

    # 14. IntentPrediction
    intent_pred = IntentPrediction(
        message_id=inbound.id,
        intent="place_order",
        confidence=0.95,
        entities={"items": ["Espresso"]},
    )
    db_session.add(intent_pred)
    await db_session.flush()

    assert intent_pred.id is not None
    assert intent_pred.intent == "place_order"

    # ConversationState helper check
    conv_state = ConversationState(
        business_id=biz.id,
        customer_id=customer.id,
        from_number="+1234567890",
        state="awaiting_confirmation",
    )
    db_session.add(conv_state)
    await db_session.flush()

    assert conv_state.id is not None
