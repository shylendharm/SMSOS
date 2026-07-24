import uuid
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Path
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_current_user
from app.core.errors import NotFoundError
from app.db.models.user import User
from app.db.models.inventory import InventoryItem, InventoryThreshold
from app.db.repositories.inventory import InventoryRepository

router = APIRouter()


class InventoryThresholdResponse(BaseModel):
    low_threshold: Decimal
    reorder_quantity: Optional[Decimal] = None


class InventoryResponse(BaseModel):
    id: str
    business_id: str
    item_name: str
    current_quantity: Decimal
    unit: str
    is_low_stock: bool
    threshold: Optional[InventoryThresholdResponse] = None
    created_at: str


class CreateInventoryItemRequest(BaseModel):
    item_name: str
    current_quantity: Decimal = Field(ge=0, default=Decimal("0.0"))
    unit: str = "units"
    low_threshold: Decimal = Field(ge=0, default=Decimal("5.0"))
    reorder_quantity: Optional[Decimal] = None


class UpdateInventoryRequest(BaseModel):
    current_quantity: Optional[Decimal] = None
    quantity_change: Optional[Decimal] = None
    unit: Optional[str] = None
    low_threshold: Optional[Decimal] = None
    reorder_quantity: Optional[Decimal] = None


def format_inventory_response(item: InventoryItem) -> dict:
    threshold_data = None
    if getattr(item, "threshold", None):
        threshold_data = {
            "low_threshold": float(item.threshold.low_threshold),
            "reorder_quantity": float(item.threshold.reorder_quantity) if item.threshold.reorder_quantity is not None else None,
        }
    return {
        "id": str(item.id),
        "business_id": str(item.business_id),
        "item_name": item.item_name,
        "current_quantity": float(item.current_quantity),
        "unit": item.unit,
        "is_low_stock": item.is_low_stock,
        "threshold": threshold_data,
        "created_at": item.created_at.isoformat(),
    }


@router.get("/inventory", response_model=List[InventoryResponse])
async def list_inventory(
    low_stock_only: bool = Query(False),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = InventoryRepository(db)
    if low_stock_only:
        items = await repo.list_low_stock(current_user.business_id)
    else:
        items = await repo.list_by_business(current_user.business_id, offset=offset, limit=limit)
    return [format_inventory_response(i) for i in items]


@router.post("/inventory", response_model=InventoryResponse)
async def create_inventory_item(
    req: CreateInventoryItemRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = InventoryRepository(db)
    is_low = req.current_quantity <= req.low_threshold

    item = InventoryItem(
        business_id=current_user.business_id,
        item_name=req.item_name,
        current_quantity=req.current_quantity,
        unit=req.unit,
        is_low_stock=is_low,
    )
    db.add(item)
    await db.flush()

    threshold = InventoryThreshold(
        item_id=item.id,
        low_threshold=req.low_threshold,
        reorder_quantity=req.reorder_quantity,
    )
    db.add(threshold)
    await db.commit()

    full_item = await repo.get_by_id_with_threshold(item.id)
    return format_inventory_response(full_item or item)


@router.patch("/inventory/{item_id}", response_model=InventoryResponse)
async def update_inventory(
    req: UpdateInventoryRequest,
    item_id: uuid.UUID = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = InventoryRepository(db)
    item = await repo.get_by_id_with_threshold(item_id)
    if not item or item.business_id != current_user.business_id:
        raise NotFoundError(f"Inventory item with id {item_id} not found")

    if req.quantity_change is not None:
        await repo.adjust_stock(item_id, req.quantity_change, source="owner_action")

    if req.current_quantity is not None:
        item.current_quantity = max(Decimal("0"), req.current_quantity)

    if req.unit is not None:
        item.unit = req.unit

    if item.threshold:
        if req.low_threshold is not None:
            item.threshold.low_threshold = req.low_threshold
        if req.reorder_quantity is not None:
            item.threshold.reorder_quantity = req.reorder_quantity

    low_thresh = item.threshold.low_threshold if item.threshold else Decimal("5.0")
    item.is_low_stock = item.current_quantity <= low_thresh

    await db.commit()
    full_item = await repo.get_by_id_with_threshold(item_id)
    return format_inventory_response(full_item or item)
