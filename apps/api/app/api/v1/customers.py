import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_current_user
from app.db.models.user import User
from app.db.models.customer import Customer
from app.db.repositories.customer import CustomerRepository

router = APIRouter()


class CustomerResponse(BaseModel):
    id: str
    business_id: str
    phone_number: str
    name: Optional[str] = None
    notes: Optional[str] = None
    created_at: str


class CreateCustomerRequest(BaseModel):
    phone_number: str
    name: Optional[str] = None
    notes: Optional[str] = None


def format_customer_response(cust: Customer) -> dict:
    return {
        "id": str(cust.id),
        "business_id": str(cust.business_id),
        "phone_number": cust.phone_number,
        "name": cust.name,
        "notes": cust.notes,
        "created_at": cust.created_at.isoformat(),
    }


@router.get("/customers", response_model=List[CustomerResponse])
async def list_customers(
    phone: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = CustomerRepository(db)
    if phone:
        customers = await repo.search_by_phone(phone, current_user.business_id)
    else:
        customers = await repo.list_by_business(current_user.business_id)
    return [format_customer_response(c) for c in customers]


@router.post("/customers", response_model=CustomerResponse)
async def create_customer(
    req: CreateCustomerRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = CustomerRepository(db)
    existing = await repo.get_by_phone(req.phone_number, current_user.business_id)
    if existing:
        if req.name:
            existing.name = req.name
        if req.notes:
            existing.notes = req.notes
        await db.commit()
        await db.refresh(existing)
        return format_customer_response(existing)

    cust = await repo.create(
        business_id=current_user.business_id,
        phone_number=req.phone_number,
        name=req.name,
        notes=req.notes,
    )
    return format_customer_response(cust)


@router.delete("/customers/{customer_id}")
async def delete_customer(
    customer_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = CustomerRepository(db)
    cust = await repo.get(customer_id)
    if not cust or cust.business_id != current_user.business_id:
        from app.core.exceptions import NotFoundError
        raise NotFoundError(f"Customer with id {customer_id} not found")
    await repo.delete(customer_id)
    return {"status": "success", "message": "Customer deleted successfully"}
