"""
Authentication API routes.
"""
import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from backend.db.database import get_db
from backend.models.schemas import UserCreate, UserResponse, Token
from backend.services.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    get_current_user,
    create_default_admin,
)

router = APIRouter(prefix="/api/auth", tags=["authentication"])

# Rate limiter for brute force protection
limiter = Limiter(key_func=get_remote_address)


@router.on_event("startup")
async def startup_event():
    """Initialize default admin user on startup."""
    await create_default_admin()


@router.post("/token", response_model=Token)
@limiter.limit("5/minute")
async def login_for_access_token(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    """Authenticate user and return JWT token."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT id, username, hashed_password, role FROM users WHERE username = ?",
            (form_data.username,)
        )
        row = await cursor.fetchone()
        if row is None or not verify_password(form_data.password, row["hashed_password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        access_token = create_access_token(
            data={"sub": row["username"], "role": row["role"]},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        return Token(access_token=access_token)


@router.post("/register", response_model=UserResponse)
@limiter.limit("3/minute")
async def register_user(request: Request, user: UserCreate):
    """Register a new user."""
    async with get_db() as db:
        # Check if username exists
        cursor = await db.execute(
            "SELECT id FROM users WHERE username = ?", (user.username,)
        )
        if await cursor.fetchone() is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        user_id = str(uuid.uuid4())
        await db.execute(
            "INSERT INTO users (id, username, hashed_password, role) VALUES (?, ?, ?, ?)",
            (user_id, user.username, get_password_hash(user.password), user.role)
        )
        await db.commit()
        return UserResponse(id=user_id, username=user.username, role=user.role)


@router.get("/me", response_model=dict)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user information."""
    return current_user
