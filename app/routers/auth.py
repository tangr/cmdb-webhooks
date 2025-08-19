from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Cookie
from typing import Optional
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from datetime import datetime, timedelta
from app.dependencies import (
    create_access_token,
    create_session_token,
    verify_session,
    get_current_user_jwt,
    get_current_user_session,
    get_current_user_flexible,
    get_oidc_discovery,
    verify_oidc_token,
    User,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from app.services.redis_session import redis_session_manager
from config.config import settings
import httpx
import secrets
from urllib.parse import urlencode

templates = Jinja2Templates(directory="templates")

# Import and register custom time filters
from app.utils.template_filters import time_to_str, time_diff_now
from app.utils.logger import get_logger

logger = get_logger(__name__)

templates.env.filters["timeToStr"] = time_to_str
templates.env.filters["timeDiffNow"] = time_diff_now

router = APIRouter()


# Request/Response models
class Token(BaseModel):
    access_token: str
    token_type: str


class UserCreate(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    user_id: str
    username: str
    roles: list[str]


def authenticate_user(username: str, password: str) -> dict:
    """Authenticate user credentials (mock implementation)"""
    user = settings.mock_users.get(username)
    if not user or user["password"] != password:
        return None
    return user


# ==================== JWT Token Authentication ====================
@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """OAuth2 compatible token endpoint for API access"""
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user["user_id"],
            "username": user["username"],
            "roles": user["roles"],
        },
        expires_delta=access_token_expires,
    )

    return {"access_token": access_token, "token_type": "bearer"}


# ==================== Session Cookie Authentication ====================
@router.post("/login")
async def login_session(
    form_data: OAuth2PasswordRequestForm = Depends(), response: Response = None
):
    """Web login endpoint that sets session cookie"""
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    # Create session in Redis
    session_token = create_session_token()
    user_data = {
        "user_id": user["user_id"],
        "username": user["username"],
        "roles": user["roles"],
    }

    # Store session in Redis with 24 hour expiration
    success = await redis_session_manager.set_session(
        session_token, user_data, expire_seconds=86400
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create session",
        )

    # Set httpOnly cookie
    response.set_cookie(
        key="session",
        value=session_token,
        max_age=86400,  # 24 hours
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
    )

    return {
        "message": "Login successful",
        "user": user_data,
    }


@router.post("/logout")
async def logout_session(
    response: Response,
    session: Optional[str] = Cookie(None),
    session_user: User = Depends(get_current_user_session),
):
    """Web logout endpoint that clears session"""
    if not session_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Delete session from Redis
    if session:
        await redis_session_manager.delete_session(session)

    # Clear session cookie
    response.delete_cookie(key="session")

    return {"message": "Logout successful"}


# ==================== User Info Endpoints ====================
@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user_flexible)):
    """Get current user info (supports both JWT and session auth)"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return UserResponse(
        user_id=current_user.user_id,
        username=current_user.username,
        roles=current_user.roles,
    )


@router.get("/me/jwt")
async def read_users_me_jwt(current_user: User = Depends(get_current_user_jwt)):
    """Get current user info via JWT only"""
    if not current_user:
        raise HTTPException(status_code=401, detail="JWT token required")

    return {
        "user_id": current_user.user_id,
        "username": current_user.username,
        "roles": current_user.roles,
        "auth_method": "jwt",
    }


@router.get("/me/session")
async def read_users_me_session(current_user: User = Depends(get_current_user_session)):
    """Get current user info via session only"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Session required")

    return {
        "user_id": current_user.user_id,
        "username": current_user.username,
        "roles": current_user.roles,
        "auth_method": "session",
    }


# ==================== Session Management ====================
@router.get("/sessions")
async def list_active_sessions():
    """List all active sessions (admin only - for demo purposes)"""
    sessions = await redis_session_manager.get_all_sessions()
    return {
        "active_sessions": len(sessions),
        "sessions": [
            {
                "token": session["token"],
                "user": session["user"]["username"],
                "created_at": session["created_at"],
                "expires_at": session["expires_at"],
                "ttl_seconds": session["ttl_seconds"],
            }
            for session in sessions
        ],
    }


@router.delete("/sessions")
async def clear_all_sessions():
    """Clear all active sessions (admin only - for demo purposes)"""
    count = await redis_session_manager.clear_all_sessions()
    return {"message": f"Cleared {count} active sessions"}


# ==================== Web Pages ====================
@router.get("/login-page", response_class=HTMLResponse)
async def login_page(
    request: Request, current_user: User = Depends(get_current_user_flexible)
):
    """Show login page"""
    # Redirect to dashboard if already logged in
    if current_user:
        return RedirectResponse(url="/auth/dashboard", status_code=302)

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "page_name": "Login",
            "oidc_login_button_text": settings.oidc_login_button_text,
        },
    )


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(
    request: Request, current_user: User = Depends(get_current_user_flexible)
):
    """Show user dashboard"""
    # Redirect to login if not authenticated
    if not current_user:
        return RedirectResponse(url="/auth/login-page", status_code=302)

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"page_name": "Dashboard", "current_user": current_user},
    )


# ==================== OIDC Authentication ====================
@router.get("/oidc/login")
async def oidc_login(request: Request):
    """Initiate OIDC login flow"""
    try:
        # Get OIDC discovery configuration
        discovery = await get_oidc_discovery()
        authorization_endpoint = discovery.get("authorization_endpoint")

        if not authorization_endpoint:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authorization endpoint not found in OIDC discovery",
            )

        # Generate state parameter for security
        state = secrets.token_urlsafe(32)

        # Store state in session or cache (for production, use Redis)
        # For now, we'll include it in the redirect and validate it in callback

        # Build authorization URL
        auth_params = {
            "response_type": "code",
            "client_id": settings.oidc_client_id,
            "redirect_uri": settings.oidc_redirect_uri,
            "scope": settings.oidc_scope,
            "state": state,
        }

        auth_url = f"{authorization_endpoint}?{urlencode(auth_params)}"

        # Store state in Redis for validation
        session_token = secrets.token_urlsafe(32)
        state_data = {"state": state}
        await redis_session_manager.set_session(
            f"oidc_state_{session_token}", state_data, expire_seconds=600
        )  # 10 minutes

        response = RedirectResponse(url=auth_url, status_code=302)
        response.set_cookie(
            key="oidc_session",
            value=session_token,
            max_age=600,  # 10 minutes
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax",
        )

        return response

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate OIDC login: {str(e)}",
        )


@router.get("/oidc/callback")
async def oidc_callback(
    request: Request,
    code: str = None,
    state: str = None,
    error: str = None,
    oidc_session: str = Cookie(None),
):
    """Handle OIDC callback"""
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OIDC authentication error: {error}",
        )

    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code not provided",
        )

    if not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="State parameter not provided",
        )

    # Validate state parameter
    if oidc_session:
        session_key = f"oidc_state_{oidc_session}"
        session_data = await redis_session_manager.get_session(session_key)
        if session_data and session_data.get("state") == state:
            # Clean up temporary session
            await redis_session_manager.delete_session(session_key)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid state parameter",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="OIDC session not found"
        )

    try:
        # Get discovery configuration
        discovery = await get_oidc_discovery()
        token_endpoint = discovery.get("token_endpoint")

        if not token_endpoint:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Token endpoint not found in OIDC discovery",
            )

        # Exchange authorization code for tokens
        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.oidc_redirect_uri,
            "client_id": settings.oidc_client_id,
            "client_secret": settings.oidc_client_secret,
        }

        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                token_endpoint,
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10,
            )
            token_response.raise_for_status()
            tokens = token_response.json()

        access_token = tokens.get("access_token")
        id_token = tokens.get("id_token")

        if not access_token or not id_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tokens not provided by OIDC provider",
            )

        # Verify ID token and extract user info
        user_info = await verify_oidc_token(id_token)
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ID token"
            )

        logger.debug(f"OIDC user login: {user_info.get('username', 'unknown')}")

        # Create session for the user in Redis
        session_token = create_session_token()
        session_user_data = {
            "user_id": user_info["user_id"],
            "username": user_info["username"],
            "roles": user_info["roles"],
            "auth_method": "oidc",
            "oidc_access_token": access_token,
        }

        success = await redis_session_manager.set_session(
            session_token, session_user_data, expire_seconds=86400
        )  # 24 hours
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create session",
            )

        logger.debug(
            f"Created session for OIDC user: {user_info.get('username', 'unknown')}"
        )

        # Create redirect response
        response = RedirectResponse(url="/auth/dashboard", status_code=302)

        # Clear OIDC session cookie and set regular session cookie
        response.delete_cookie(key="oidc_session")
        response.set_cookie(
            key="session",
            value=session_token,
            max_age=86400,  # 24 hours
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax",
        )

        logger.debug(
            f"Set session cookie for OIDC user: {user_info.get('username', 'unknown')}"
        )

        return response

    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Token exchange failed: {e.response.text}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OIDC callback processing failed: {str(e)}",
        )


# Root redirect
@router.get("/")
async def root(current_user: User = Depends(get_current_user_flexible)):
    """Root redirect - go to dashboard if logged in, otherwise login"""
    if current_user:
        return RedirectResponse(url="/auth/dashboard", status_code=302)
    else:
        return RedirectResponse(url="/auth/login-page", status_code=302)
