from typing import AsyncGenerator
from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db_session
from app.core.security import decode_access_token
from app.core.errors import AuthError
from app.db.repositories.user import UserRepository
from app.db.models.user import User


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db_session():
        yield session


async def get_current_user(
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization:
        raise AuthError("Missing authorization header")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthError("Invalid authorization format. Use 'Bearer <token>'")

    token = parts[1]
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise AuthError("Invalid or expired access token")

    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(payload["sub"])
    if not user or not user.is_active:
        raise AuthError("User not found or inactive")

    return user