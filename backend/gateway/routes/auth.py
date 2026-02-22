"""Authentication routes."""

import logging
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.shared.database import get_db
from backend.shared.models import User, UserRole

from ..auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    hash_password,
    require_role,
    verify_password,
)

# Pre-computed dummy hash for constant-time user enumeration prevention.
# Avoids recalculating bcrypt hash on every failed login attempt.
_DUMMY_HASH = hash_password("dummy-constant-time-padding")

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


# Request/Response schemas (auth-specific)
class RegisterRequest(BaseModel):
    """Schema for user registration."""

    email: EmailStr
    password: str
    display_name: str = Field(min_length=2, max_length=100)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password complexity."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v


class LoginRequest(BaseModel):
    """Schema for user login."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Schema for token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Schema for token refresh."""

    refresh_token: str


class UserResponse(BaseModel):
    """Schema for user profile response."""

    id: str
    email: str
    display_name: str
    role: str


class UpdateRoleRequest(BaseModel):
    """Schema for updating a user's role (admin only)."""

    role: UserRole


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user."""
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Create user
    user = User(
        id=uuid.uuid4(),
        email=request.email,
        hashed_password=hash_password(request.password),
        display_name=request.display_name,
        role=UserRole.FREE,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Generate tokens
    access_token = create_access_token(str(user.id), user.role.value)
    refresh_token = create_refresh_token(str(user.id))

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login and get tokens."""
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    if not user:
        # Constant-time: run dummy verify to prevent timing-based user enumeration
        verify_password(request.password, _DUMMY_HASH)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    access_token = create_access_token(str(user.id), user.role.value)
    refresh_token = create_refresh_token(str(user.id))

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Refresh access token."""
    payload = decode_token(request.refresh_token)

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id = payload.get("sub")
    try:
        user_uuid = uuid.UUID(user_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    access_token = create_access_token(str(user.id), user.role.value)
    new_refresh_token = create_refresh_token(str(user.id))

    return TokenResponse(access_token=access_token, refresh_token=new_refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user profile."""
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        display_name=current_user.display_name,
        role=current_user.role.value,
    )


@router.put(
    "/users/{user_id}/role",
    response_model=UserResponse,
    dependencies=[Depends(require_role([UserRole.ADMIN]))],
)
async def update_user_role(
    user_id: uuid.UUID,
    request: UpdateRoleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a user's role (admin only)."""
    # Prevent admin from demoting themselves
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    old_role = target_user.role.value
    target_user.role = request.role
    await db.commit()
    await db.refresh(target_user)

    logger.info(
        "Role changed: admin=%s target=%s old_role=%s new_role=%s",
        current_user.id,
        user_id,
        old_role,
        request.role.value,
    )

    return UserResponse(
        id=str(target_user.id),
        email=target_user.email,
        display_name=target_user.display_name,
        role=target_user.role.value,
    )
