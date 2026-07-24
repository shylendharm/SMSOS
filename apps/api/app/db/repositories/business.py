from sqlalchemy.future import select
from app.db.repositories.base import BaseRepository
from app.db.models.business import Business, BusinessSettings
import uuid


class BusinessRepository(BaseRepository[Business]):
    def __init__(self, db):
        super().__init__(Business, db)

    async def get_by_phone(self, phone_number: str) -> Business | None:
        result = await self.db.execute(
            select(Business).where(
                Business.phone_number == phone_number.replace("whatsapp:", ""),
                Business.is_active == True,
            )
        )
        return result.scalars().first()

    async def get_with_settings(self, business_id: uuid.UUID) -> Business | None:
        from sqlalchemy.orm import selectinload
        result = await self.db.execute(
            select(Business).where(Business.id == business_id).options(selectinload(Business.settings))
        )
        return result.scalars().first()