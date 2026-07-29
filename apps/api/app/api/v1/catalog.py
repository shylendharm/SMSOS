import uuid
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_current_user
from app.core.errors import NotFoundError
from app.db.models.user import User
from app.db.models.catalog import CatalogItem
from app.db.repositories.catalog import CatalogRepository

router = APIRouter()


class CatalogItemResponse(BaseModel):
    id: str
    business_id: str
    name: str
    description: Optional[str] = None
    price: Decimal
    unit: str
    category: str
    is_available: bool
    created_at: str


class CreateCatalogItemRequest(BaseModel):
    name: str
    description: Optional[str] = None
    price: Decimal = Field(ge=0, default=Decimal("0.0"))
    unit: str = "piece"
    category: str = "General"
    is_available: bool = True


def format_catalog_response(item: CatalogItem) -> dict:
    return {
        "id": str(item.id),
        "business_id": str(item.business_id),
        "name": item.name,
        "description": item.description,
        "price": float(item.price),
        "unit": item.unit,
        "category": item.category,
        "is_available": item.is_available,
        "created_at": item.created_at.isoformat(),
    }


@router.get("/catalog", response_model=List[CatalogItemResponse])
async def list_catalog(
    only_available: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = CatalogRepository(db)
    items = await repo.list_by_business(current_user.business_id, only_available=only_available)
    return [format_catalog_response(i) for i in items]


@router.post("/catalog", response_model=CatalogItemResponse)
async def create_catalog_item(
    req: CreateCatalogItemRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = CatalogRepository(db)
    item = await repo.create(
        business_id=current_user.business_id,
        name=req.name,
        description=req.description,
        price=req.price,
        unit=req.unit,
        category=req.category,
        is_available=req.is_available,
    )
    return format_catalog_response(item)

class UpdateCatalogItemRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    unit: Optional[str] = None
    category: Optional[str] = None
    is_available: Optional[bool] = None


@router.patch("/catalog/{item_id}", response_model=CatalogItemResponse)
async def update_catalog_item(
    req: UpdateCatalogItemRequest,
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = CatalogRepository(db)
    item = await repo.get(item_id)
    if not item or item.business_id != current_user.business_id:
        raise NotFoundError(f"Catalog item with id {item_id} not found")

    if req.name is not None:
        item.name = req.name
    if req.description is not None:
        item.description = req.description
    if req.price is not None:
        item.price = req.price
    if req.unit is not None:
        item.unit = req.unit
    if req.category is not None:
        item.category = req.category
    if req.is_available is not None:
        item.is_available = req.is_available

    await db.commit()
    await db.refresh(item)
    return format_catalog_response(item)


@router.delete("/catalog/{item_id}")
async def delete_catalog_item(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = CatalogRepository(db)
    item = await repo.get(item_id)
    if not item or item.business_id != current_user.business_id:
        from app.core.exceptions import NotFoundError
        raise NotFoundError(f"Catalog item with id {item_id} not found")
    await repo.delete(item_id)
    return {"status": "success", "message": "Item deleted successfully"}
