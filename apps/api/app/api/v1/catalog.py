import uuid
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_current_user
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
