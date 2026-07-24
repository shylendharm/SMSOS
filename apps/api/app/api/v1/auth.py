from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db
from app.core.security import verify_password, create_access_token
from app.core.errors import AuthError
from app.db.repositories.user import UserRepository

router = APIRouter()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: str
    business_id: str
    name: str


@router.post("/auth/login", response_model=LoginResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(req.email)
    if not user:
        raise AuthError("Invalid email or password")

    if not verify_password(req.password, user.hashed_password):
        raise AuthError("Invalid email or password")

    if not user.is_active:
        raise AuthError("User account is inactive")

    token = create_access_token(subject=user.email, role=user.role)
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        role=user.role,
        user_id=str(user.id),
        business_id=str(user.business_id),
        name=user.name,
    )
