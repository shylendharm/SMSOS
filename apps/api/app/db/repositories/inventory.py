import re
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.db.repositories.base import BaseRepository
from app.db.models.inventory import InventoryItem, InventoryThreshold, InventoryEvent
import uuid
from decimal import Decimal


class InventoryRepository(BaseRepository[InventoryItem]):
    def __init__(self, db):
        super().__init__(InventoryItem, db)

    async def get_by_name(self, item_name: str, business_id: uuid.UUID) -> InventoryItem | None:
        all_items = await self.list_by_business(business_id)
        if not all_items:
            return None
        search_raw = item_name.lower().strip()
        clean_search = re.sub(r'[^a-zA-Z0-9]', '', search_raw)
        for item in all_items:
            if item.item_name.lower().strip() == search_raw:
                return item
        for item in all_items:
            clean_item = re.sub(r'[^a-zA-Z0-9]', '', item.item_name.lower())
            if clean_item == clean_search:
                return item
        for item in all_items:
            clean_item = re.sub(r'[^a-zA-Z0-9]', '', item.item_name.lower())
            if len(clean_search) >= 3 and (clean_search in clean_item or clean_item in clean_search):
                return item
        return None

    async def get_by_id_with_threshold(self, item_id: uuid.UUID) -> InventoryItem | None:
        result = await self.db.execute(
            select(InventoryItem).where(InventoryItem.id == item_id).options(selectinload(InventoryItem.threshold))
        )
        return result.scalars().first()

    async def list_by_business(self, business_id: uuid.UUID, offset: int = 0, limit: int = 100) -> list[InventoryItem]:
        result = await self.db.execute(
            select(InventoryItem)
            .where(InventoryItem.business_id == business_id)
            .options(selectinload(InventoryItem.threshold))
            .offset(offset).limit(limit)
        )
        return list(result.scalars().all())

    async def list_low_stock(self, business_id: uuid.UUID) -> list[InventoryItem]:
        result = await self.db.execute(
            select(InventoryItem)
            .where(InventoryItem.business_id == business_id, InventoryItem.is_low_stock == True)
            .options(selectinload(InventoryItem.threshold))
        )
        return list(result.scalars().all())

    async def adjust_stock(self, item_id: uuid.UUID, quantity_change: Decimal, source: str = "manual", notes: str | None = None) -> InventoryItem | None:
        item = await self.get(item_id)
        if not item:
            return None
        new_qty = max(Decimal("0"), item.current_quantity + quantity_change)
        item.current_quantity = new_qty
        event = InventoryEvent(
            item_id=item.id,
            event_type="adjustment" if quantity_change >= 0 else "deduction",
            quantity_change=quantity_change,
            quantity_after=new_qty,
            source=source,
            notes=notes,
        )
        self.db.add(event)
        await self.db.flush()
        return item