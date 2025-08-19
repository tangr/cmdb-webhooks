from fastapi import Header, HTTPException, Depends, status, Cookie
from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials,
    OAuth2PasswordBearer,
)
from config.config import get_session, settings
from typing import Annotated, Optional, Union
from sqlmodel import Session
from jose import JWTError, jwt
from datetime import datetime, timedelta
import secrets
import httpx
from authlib.jose import jwt as authlib_jwt
from authlib.jose.errors import JoseError

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
from app.services.redis_session import redis_session_manager


def create_session_token() -> str:
    """Create secure session token"""
    return redis_session_manager.create_session_token()


async def verify_session(session_token: str) -> Optional[dict]:
    """Verify session token using Redis"""
    print(f"Verifying session token: {session_token}")  # Debug logging

    user_data = await redis_session_manager.get_session(session_token)
    if not user_data:
        print("Session not found in Redis")  # Debug logging
        return None

    print("Session verified successfully")  # Debug logging
    return user_data


async def get_current_user_session(
    session: Optional[str] = Cookie(None),
) -> Optional[User]:
    """Get current user from session cookie (optional)"""
    print(f"Session cookie received: {session}")  # Debug logging
    if not session:
        print("No session cookie found")  # Debug logging
        return None

    user_data = await verify_session(session)
    print(f"Session data: {user_data}")  # Debug logging
    if not user_data:
        print("Session verification failed")  # Debug logging
        return None

    return User(
        user_id=user_data["user_id"],
        username=user_data["username"],
        roles=user_data["roles"],
    )


# ==================== 3.5. OIDC Token Authentication ====================
async def get_current_user_oidc(
    authorization: Optional[str] = Header(None),
) -> Optional[User]:
    """Get current user from OIDC token (optional)"""
    if not authorization:
        return None

    # Extract Bearer token
    if not authorization.startswith("Bearer "):
        return None

    token = authorization[7:]  # Remove "Bearer " prefix

    user_info = await verify_oidc_token(token)
    if not user_info:
        return None

    return User(
        user_id=user_info["user_id"],
        username=user_info["username"],
        roles=user_info["roles"],
    )


# ==================== 4. Flexible Authentication (Try Multiple Methods) ====================
async def get_current_user_flexible(
    # Try JWT token first
    jwt_user: Optional[User] = Depends(get_current_user_jwt),
    # Try session cookie
    session_user: Optional[User] = Depends(get_current_user_session),
    # Try OIDC token
    oidc_user: Optional[User] = Depends(get_current_user_oidc),
) -> Optional[User]:
    """Try multiple authentication methods, return first valid user"""
    return jwt_user or session_user or oidc_user


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


# ==================== 6. OIDC Authentication ====================
# OIDC discovery cache
_oidc_discovery_cache = None
_oidc_jwks_cache = None
_cache_timestamp = None
CACHE_DURATION = 3600  # 1 hour


async def get_oidc_discovery():
    """Get OIDC discovery configuration with caching"""
    global _oidc_discovery_cache, _cache_timestamp

    now = datetime.utcnow().timestamp()
    if (
        _oidc_discovery_cache is None
        or _cache_timestamp is None
        or now - _cache_timestamp > CACHE_DURATION
    ):

        try:
            async with httpx.AsyncClient() as client:
                discovery_url = (
                    f"{settings.oidc_issuer_url}/.well-known/openid-configuration"
                )
                response = await client.get(discovery_url, timeout=10)
                response.raise_for_status()
                _oidc_discovery_cache = response.json()
                _cache_timestamp = now
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch OIDC discovery: {str(e)}",
            )

    return _oidc_discovery_cache


async def get_oidc_jwks():
    """Get OIDC JWKS with caching"""
    global _oidc_jwks_cache, _cache_timestamp

    now = datetime.utcnow().timestamp()
    if (
        _oidc_jwks_cache is None
        or _cache_timestamp is None
        or now - _cache_timestamp > CACHE_DURATION
    ):

        discovery = await get_oidc_discovery()
        jwks_uri = discovery.get("jwks_uri")

        if not jwks_uri:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="JWKS URI not found in OIDC discovery",
            )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(jwks_uri, timeout=10)
                response.raise_for_status()
                _oidc_jwks_cache = response.json()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch OIDC JWKS: {str(e)}",
            )

    return _oidc_jwks_cache


async def verify_oidc_token(token: str) -> Optional[dict]:
    """Verify OIDC token and return user info"""
    try:
        # Get JWKS for token verification
        jwks = await get_oidc_jwks()
        discovery = await get_oidc_discovery()

        # Verify token using authlib
        claims = authlib_jwt.decode(
            token,
            jwks,
            claims_options={
                "iss": {"essential": True, "value": settings.oidc_issuer_url},
                "aud": {"essential": True, "value": settings.oidc_client_id},
            },
        )

        # Debug: Print all available claims
        print(f"OIDC Claims: {claims}")  # Debug logging

        # Extract user information - prioritize preferred_username, then username, then email
        preferred_username = claims.get("preferred_username")
        username_claim = claims.get("username")  # Some providers use 'username' instead
        name = claims.get("name")
        email = claims.get("email")
        sub = claims.get("sub")

        # Use preferred_username first, then username, then name, then email, finally sub
        username = preferred_username or username_claim or name or email or sub

        print(
            f"Username selection - preferred_username: {preferred_username}, username: {username_claim}, name: {name}, email: {email}, final: {username}"
        )  # Debug logging

        user_info = {
            "user_id": sub,
            "username": username,
            "email": email,
            "name": claims.get("name"),
            "roles": ["user"],  # Default role, can be customized based on claims
        }

        # Check for admin role based on groups or other claims
        groups = claims.get("groups", [])
        if isinstance(groups, list) and "admin" in groups:
            user_info["roles"].append("admin")

        return user_info

    except JoseError as e:
        return None
    except Exception as e:
        return None


# Legacy function (kept for compatibility)
async def get_query_token(token: str):
    if token != "jessica":
        raise HTTPException(status_code=400, detail="No Jessica token provided")
