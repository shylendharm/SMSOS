from sqlalchemy.future import select
from app.db.repositories.base import BaseRepository
from app.db.models.user import User
import uuid


class UserRepository(BaseRepository[User]):
    def __init__(self, db):
        super().__init__(User, db)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalars().first()

    async def list_by_business(self, business_id: uuid.UUID) -> list[User]:
        result = await self.db.execute(select(User).where(User.business_id == business_id))
        return list(result.scalars().all())