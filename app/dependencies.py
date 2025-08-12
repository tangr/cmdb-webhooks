from fastapi import Header, HTTPException, Depends, status, Cookie
from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials,
    OAuth2PasswordBearer,
)
from config.config import get_session
from typing import Annotated, Optional, Union
from sqlmodel import Session
from jose import JWTError, jwt
from datetime import datetime, timedelta
import secrets

SessionDep = Annotated[Session, Depends(get_session)]

# OAuth2 and JWT settings
SECRET_KEY = "your-secret-key-here-please-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)
security = HTTPBearer(auto_error=False)


# User model for JWT payload
class User:
    def __init__(self, user_id: str, username: str, roles: list = None):
        self.user_id = user_id
        self.username = username
        self.roles = roles or []


# ==================== 1. X-Token Authentication (Internal Services) ====================
async def get_token_header(x_token: str = Header()):
    """Internal service authentication via X-Token header"""
    if x_token != "fake-super-secret-token":
        raise HTTPException(status_code=400, detail="X-Token header invalid")
    return {"auth_type": "x_token", "service": "internal"}


# ==================== 2. OAuth2 JWT Authentication (API Users) ====================
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """Verify JWT token and return payload"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        username: str = payload.get("username")
        if user_id is None or username is None:
            return None
        return {
            "user_id": user_id,
            "username": username,
            "roles": payload.get("roles", []),
        }
    except JWTError:
        return None


async def get_current_user_jwt(
    token: Optional[str] = Depends(oauth2_scheme),
) -> Optional[User]:
    """Get current user from JWT token (optional)"""
    if not token:
        return None

    payload = verify_token(token)
    if not payload:
        return None

    return User(
        user_id=payload["user_id"], username=payload["username"], roles=payload["roles"]
    )


async def get_current_user_required(token: str = Depends(oauth2_scheme)) -> User:
    """Get current user from JWT token (required)"""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return User(
        user_id=payload["user_id"], username=payload["username"], roles=payload["roles"]
    )


# ==================== 3. Session Cookie Authentication (Web Users) ====================
ACTIVE_SESSIONS = {}  # In production, use Redis or database


def create_session_token() -> str:
    """Create secure session token"""
    return secrets.token_urlsafe(32)


def verify_session(session_token: str) -> Optional[dict]:
    """Verify session token"""
    session_data = ACTIVE_SESSIONS.get(session_token)
    if not session_data:
        return None

    # Check expiration
    if datetime.utcnow() > session_data["expires"]:
        del ACTIVE_SESSIONS[session_token]
        return None

    return session_data["user"]


async def get_current_user_session(
    session: Optional[str] = Cookie(None),
) -> Optional[User]:
    """Get current user from session cookie (optional)"""
    if not session:
        return None

    user_data = verify_session(session)
    if not user_data:
        return None

    return User(
        user_id=user_data["user_id"],
        username=user_data["username"],
        roles=user_data["roles"],
    )


# ==================== 4. Flexible Authentication (Try Multiple Methods) ====================
async def get_current_user_flexible(
    # Try JWT token first
    jwt_user: Optional[User] = Depends(get_current_user_jwt),
    # Try session cookie
    session_user: Optional[User] = Depends(get_current_user_session),
) -> Optional[User]:
    """Try multiple authentication methods, return first valid user"""
    return jwt_user or session_user


async def get_current_user_any_required(
    user: Optional[User] = Depends(get_current_user_flexible),
) -> User:
    """Require authentication via any supported method"""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return user


# ==================== 5. Role-based Access Control ====================
def require_roles(*required_roles: str):
    """Decorator factory for role-based access control"""

    async def role_checker(user: User = Depends(get_current_user_any_required)):
        if not any(role in user.roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {required_roles}",
            )
        return user

    return role_checker


# Legacy function (kept for compatibility)
async def get_query_token(token: str):
    if token != "jessica":
        raise HTTPException(status_code=400, detail="No Jessica token provided")
