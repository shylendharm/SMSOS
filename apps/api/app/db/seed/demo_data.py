import uuid
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import async_session
from app.db.base import Base
from app.db.models.business import Business, BusinessSettings
from app.db.models.user import User
from app.db.models.customer import Customer
from app.db.models.catalog import CatalogItem
from app.db.models.inventory import InventoryItem, InventoryThreshold
from app.db.models.order import Order, OrderItem
from app.db.models.reservation import Reservation
from app.core.security import hash_password
from app.core.logging import logger


async def seed_demo_data():
    async with async_session() as db:
        # Check if already seeded
        from sqlalchemy.future import select
        existing = await db.execute(select(Business).limit(1))
        if existing.scalars().first():
            logger.info("seed_skipped", reason="data already exists")
            return

        biz_id = uuid.uuid4()
        owner_phone = "+919876543210"

        business = Business(
            id=biz_id,
            name="SMSOS Demo Diner",
            business_type="restaurant",
            phone_number="+16414065455",
            timezone="Asia/Kolkata",
            locale="en",
            is_active=True,
        )
        db.add(business)

        settings = BusinessSettings(
            business_id=biz_id,
            table_count=8,
            sms_aliases={"cake": "Chocolate Cake", "espresso": "Espresso", "coffee": "Espresso"},
            notification_preferences={"owner_phones": [owner_phone]},
        )
        db.add(settings)

        admin = User(
            business_id=biz_id,
            email="owner@smsos.in",
            hashed_password=hash_password("admin123"),
            name="Owner",
            role="owner",
        )
        db.add(admin)

        customer = Customer(
            business_id=biz_id,
            phone_number=owner_phone,
            name="Demo Customer",
        )
        db.add(customer)

        catalog_items = [
            CatalogItem(business_id=biz_id, name="Chocolate Cake", price=Decimal("350.00"), unit="kg", category="Desserts"),
            CatalogItem(business_id=biz_id, name="Espresso", price=Decimal("120.00"), unit="cup", category="Beverages"),
            CatalogItem(business_id=biz_id, name="Masala Dosa", price=Decimal("180.00"), unit="piece", category="Main Course"),
            CatalogItem(business_id=biz_id, name="Idli (2 pcs)", price=Decimal("60.00"), unit="plate", category="Main Course"),
            CatalogItem(business_id=biz_id, name="Filter Coffee", price=Decimal("40.00"), unit="cup", category="Beverages"),
        ]
        for ci in catalog_items:
            db.add(ci)
        await db.flush()

        oil = InventoryItem(business_id=biz_id, item_name="Cooking Oil", current_quantity=Decimal("3.00"), unit="liters", is_low_stock=True)
        flour = InventoryItem(business_id=biz_id, item_name="All-Purpose Flour", current_quantity=Decimal("10.00"), unit="kg")
        rice = InventoryItem(business_id=biz_id, item_name="Basmati Rice", current_quantity=Decimal("25.00"), unit="kg")
        db.add_all([oil, flour, rice])
        await db.flush()

        db.add(InventoryThreshold(item_id=oil.id, low_threshold=Decimal("5.0"), reorder_quantity=Decimal("10.0")))
        await db.flush()

        order = Order(
            business_id=biz_id,
            customer_id=customer.id,
            order_number=1,
            status="pending",
            total_amount=Decimal("470.00"),
        )
        db.add(order)
        await db.flush()

        db.add(OrderItem(order_id=order.id, item_name="Chocolate Cake", quantity=1, unit_price=Decimal("350.00")))
        db.add(OrderItem(order_id=order.id, item_name="Espresso", quantity=1, unit_price=Decimal("120.00")))
        await db.flush()

        res_time = datetime.now(timezone.utc) + timedelta(hours=3)
        res = Reservation(
            business_id=biz_id,
            customer_id=customer.id,
            customer_name="Demo Customer",
            reserved_at=res_time,
            table_or_slot="3",
            party_size=2,
            status="confirmed",
        )
        db.add(res)
        await db.commit()

        logger.info("seed_complete", business_id=str(biz_id))


if __name__ == "__main__":
    import asyncio
    asyncio.run(seed_demo_data())