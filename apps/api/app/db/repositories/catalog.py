from sqlalchemy.future import select
from app.db.repositories.base import BaseRepository
from app.db.models.catalog import CatalogItem
import uuid


class CatalogRepository(BaseRepository[CatalogItem]):
    def __init__(self, db):
        super().__init__(CatalogItem, db)

    async def get_by_name(self, name: str, business_id: uuid.UUID) -> CatalogItem | None:
        result = await self.db.execute(
            select(CatalogItem).where(
                CatalogItem.business_id == business_id,
                CatalogItem.name.ilike(name),
            )
        )
        return result.scalars().first()

    async def list_by_business(self, business_id: uuid.UUID, only_available: bool = False) -> list[CatalogItem]:
        q = select(CatalogItem).where(CatalogItem.business_id == business_id)
        if only_available:
            q = q.where(CatalogItem.is_available == True)
        q = q.order_by(CatalogItem.category.asc(), CatalogItem.name.asc())
        result = await self.db.execute(q)
        return list(result.scalars().all())