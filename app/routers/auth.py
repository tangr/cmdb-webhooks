from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from datetime import datetime, timedelta
from app.dependencies import (
    create_access_token, create_session_token, verify_session,
    get_current_user_jwt, get_current_user_session, get_current_user_flexible,
    User, ACTIVE_SESSIONS, ACCESS_TOKEN_EXPIRE_MINUTES
)

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

# Mock user database (replace with real database)
MOCK_USERS = {
    "testuser": {
        "user_id": "1",
        "username": "testuser", 
        "password": "testpass",  # In production, use hashed passwords
        "roles": ["user"]
    },
    "admin": {
        "user_id": "2",
        "username": "admin",
        "password": "admin123",
        "roles": ["admin", "user"]
    }
}

def authenticate_user(username: str, password: str) -> dict:
    """Authenticate user credentials (mock implementation)"""
    user = MOCK_USERS.get(username)
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
            "roles": user["roles"]
        },
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

# ==================== Session Cookie Authentication ====================
@router.post("/login")
async def login_session(form_data: OAuth2PasswordRequestForm = Depends(), response: Response = None):
    """Web login endpoint that sets session cookie"""
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    # Create session
    session_token = create_session_token()
    session_expires = datetime.utcnow() + timedelta(hours=24)
    
    ACTIVE_SESSIONS[session_token] = {
        "user": {
            "user_id": user["user_id"],
            "username": user["username"],
            "roles": user["roles"]
        },
        "expires": session_expires
    }
    
    # Set httpOnly cookie
    response.set_cookie(
        key="session",
        value=session_token,
        max_age=86400,  # 24 hours
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax"
    )
    
    return {
        "message": "Login successful",
        "user": {
            "user_id": user["user_id"],
            "username": user["username"],
            "roles": user["roles"]
        }
    }

@router.post("/logout")
async def logout_session(response: Response, session_user: User = Depends(get_current_user_session)):
    """Web logout endpoint that clears session"""
    if not session_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
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
        roles=current_user.roles
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
        "auth_method": "jwt"
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
        "auth_method": "session"
    }

# ==================== Session Management ====================
@router.get("/sessions")
async def list_active_sessions():
    """List all active sessions (admin only - for demo purposes)"""
    return {
        "active_sessions": len(ACTIVE_SESSIONS),
        "sessions": [
            {
                "user": session["user"]["username"],
                "expires": session["expires"].isoformat()
            }
            for session in ACTIVE_SESSIONS.values()
        ]
    }

@router.delete("/sessions")
async def clear_all_sessions():
    """Clear all active sessions (admin only - for demo purposes)"""
    count = len(ACTIVE_SESSIONS)
    ACTIVE_SESSIONS.clear()
    return {"message": f"Cleared {count} active sessions"}