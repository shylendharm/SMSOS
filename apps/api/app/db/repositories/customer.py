from sqlalchemy.future import select
from app.db.repositories.base import BaseRepository
from app.db.models.customer import Customer
import uuid


class CustomerRepository(BaseRepository[Customer]):
    def __init__(self, db):
        super().__init__(Customer, db)

    async def get_by_phone(self, phone_number: str, business_id: uuid.UUID) -> Customer | None:
        result = await self.db.execute(
            select(Customer).where(
                Customer.business_id == business_id,
                Customer.phone_number == phone_number,
            )
        )
        return result.scalars().first()

    async def list_by_business(self, business_id: uuid.UUID) -> list[Customer]:
        result = await self.db.execute(
            select(Customer).where(Customer.business_id == business_id)
        )
        return list(result.scalars().all())

    async def search_by_phone(self, phone_number: str, business_id: uuid.UUID) -> list[Customer]:
        result = await self.db.execute(
            select(Customer).where(
                Customer.business_id == business_id,
                Customer.phone_number.ilike(f"%{phone_number}%"),
            )
        )
        return list(result.scalars().all())