"""
Authentication and authorization service.
"""
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from backend.db.database import get_db

# Security: JWT secret must be set via environment variable
SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
if SECRET_KEY is None:
    raise RuntimeError(
        "JWT_SECRET_KEY environment variable must be set. "
        "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__ident="2b")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/token")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    # Truncate to 72 bytes (bcrypt limit) for verification
    truncated = plain_password.encode('utf-8')[:72].decode('utf-8', errors='ignore')
    return pwd_context.verify(truncated, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    # Truncate to 72 bytes (bcrypt limit) before hashing
    truncated = password.encode('utf-8')[:72].decode('utf-8', errors='ignore')
    return pwd_context.hash(truncated)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Get current user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role", "operator")
        if username is None:
            raise credentials_exception
        return {"username": username, "role": role}
    except JWTError:
        raise credentials_exception


async def get_current_active_user(current_user: dict = Depends(get_current_user)) -> dict:
    """Get current active user."""
    return current_user


def require_role(required_role: str):
    """Dependency to require a specific role."""
    async def role_checker(current_user: dict = Depends(get_current_user)) -> dict:
        role_hierarchy = {"admin": 3, "engineer": 2, "operator": 1}
        user_level = role_hierarchy.get(current_user.get("role", ""), 0)
        required_level = role_hierarchy.get(required_role, 0)
        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' or higher required"
            )
        return current_user
    return role_checker


async def create_default_admin():
    """Create default admin user if not exists.

    Security: Admin password must be set via ADMIN_PASSWORD environment variable.
    """
    admin_password = os.environ.get("ADMIN_PASSWORD")
    if admin_password is None:
        raise RuntimeError(
            "ADMIN_PASSWORD environment variable must be set for initial admin setup. "
            "Set a strong password: export ADMIN_PASSWORD='your-secure-password'"
        )

    async with get_db() as db:
        cursor = await db.execute(
            "SELECT id FROM users WHERE username = ?", ("admin",)
        )
        row = await cursor.fetchone()
        if row is None:
            await db.execute(
                "INSERT INTO users (id, username, hashed_password, role) VALUES (?, ?, ?, ?)",
                (str(uuid.uuid4()), "admin", get_password_hash(admin_password), "admin")
            )
            await db.commit()
