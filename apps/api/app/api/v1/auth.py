import uuid
from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.dependencies import get_db, get_current_user
from app.core.security import verify_password, create_access_token, hash_password
from app.core.errors import AuthError, ConflictError, NotFoundError
from app.db.models.user import User
from app.db.models.business import Business, BusinessSettings
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


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    name: str


class OnboardingRequest(BaseModel):
    business_name: str
    phone_number: str
    location: Optional[str] = None


class ProfileResponse(BaseModel):
    user_id: str
    email: str
    name: str
    role: str
    business_id: str
    business_name: str
    phone_number: str
    location: Optional[str] = None


class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    business_name: Optional[str] = None
    phone_number: Optional[str] = None
    location: Optional[str] = None


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


@router.post("/auth/signup", response_model=LoginResponse)
async def signup(req: SignupRequest, db: AsyncSession = Depends(get_db)):
    user_repo = UserRepository(db)
    existing = await user_repo.get_by_email(req.email)
    if existing:
        raise ConflictError("An account with this email already exists")

    temp_phone = f"+1555{str(uuid.uuid4())[:8]}"
    business = Business(
        name="My Store",
        business_type="retail",
        phone_number=temp_phone,
        location="",
    )
    db.add(business)
    await db.flush()

    settings = BusinessSettings(
        business_id=business.id,
        table_count=10,
    )
    db.add(settings)

    hashed_pw = hash_password(req.password)
    user = User(
        business_id=business.id,
        email=req.email,
        hashed_password=hashed_pw,
        name=req.name,
        role="owner",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(subject=user.email, role=user.role)
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        role=user.role,
        user_id=str(user.id),
        business_id=str(user.business_id),
        name=user.name,
    )


@router.post("/auth/onboarding", response_model=ProfileResponse)
async def onboarding(
    req: OnboardingRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(Business).where(Business.id == current_user.business_id))
    business = res.scalars().first()
    if not business:
        raise NotFoundError("Business not found")

    business.name = req.business_name
    business.phone_number = req.phone_number
    if req.location is not None:
        business.location = req.location

    await db.commit()
    await db.refresh(business)

    return ProfileResponse(
        user_id=str(current_user.id),
        email=current_user.email,
        name=current_user.name,
        role=current_user.role,
        business_id=str(business.id),
        business_name=business.name,
        phone_number=business.phone_number,
        location=business.location,
    )


@router.get("/auth/profile", response_model=ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(Business).where(Business.id == current_user.business_id))
    business = res.scalars().first()

    return ProfileResponse(
        user_id=str(current_user.id),
        email=current_user.email,
        name=current_user.name,
        role=current_user.role,
        business_id=str(current_user.business_id),
        business_name=business.name if business else "",
        phone_number=business.phone_number if business else "",
        location=business.location if business else "",
    )


@router.put("/auth/profile", response_model=ProfileResponse)
async def update_profile(
    req: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if req.name:
        current_user.name = req.name
    if req.email:
        current_user.email = req.email
    if req.password:
        current_user.hashed_password = hash_password(req.password)

    res = await db.execute(select(Business).where(Business.id == current_user.business_id))
    business = res.scalars().first()
    if business:
        if req.business_name:
            business.name = req.business_name
        if req.phone_number:
            business.phone_number = req.phone_number
        if req.location is not None:
            business.location = req.location

    await db.commit()
    await db.refresh(current_user)
    if business:
        await db.refresh(business)

    return ProfileResponse(
        user_id=str(current_user.id),
        email=current_user.email,
        name=current_user.name,
        role=current_user.role,
        business_id=str(current_user.business_id),
        business_name=business.name if business else "",
        phone_number=business.phone_number if business else "",
        location=business.location if business else "",
    )
