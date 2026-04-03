import pytest
from unittest.mock import patch, Mock, AsyncMock
from fastapi import status
from httpx import AsyncClient
import json
from datetime import datetime, timedelta


class TestJWTAuthentication:
    """Test JWT token-based authentication"""

    @patch("app.dependencies.verify_token")
    def test_login_for_access_token_success(self, mock_verify, client):
        """Test successful JWT token login"""
        response = client.post(
            "/auth/token", data={"username": "testuser", "password": "testpass"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_for_access_token_invalid_credentials(self, client):
        """Test JWT token login with invalid credentials"""
        response = client.post(
            "/auth/token", data={"username": "testuser", "password": "wrongpass"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Incorrect username or password" in response.json()["detail"]

    def test_login_for_access_token_disabled(self, client):
        """Test JWT token login when username/password auth is disabled"""
        with patch("config.config.settings.enable_username_password_login", False):
            response = client.post(
                "/auth/token", data={"username": "testuser", "password": "testpass"}
            )

            assert response.status_code == status.HTTP_404_NOT_FOUND


class TestSessionAuthentication:
    """Test session-based authentication"""

    @pytest.mark.asyncio
    async def test_login_session_success(self, async_client, mock_redis):
        """Test successful session login"""
        # Mock Redis operations
        mock_redis.set = AsyncMock(return_value=True)

        response = await async_client.post(
            "/auth/login", data={"username": "testuser", "password": "testpass"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Login successful"
        assert "user" in data
        assert data["user"]["username"] == "testuser"

        # Check cookie is set
        assert "session" in response.cookies

    @pytest.mark.asyncio
    async def test_logout_session_success(
        self, async_client, mock_redis, mock_session_data
    ):
        """Test successful session logout"""
        # Mock Redis operations
        mock_redis.get = AsyncMock(return_value=json.dumps(mock_session_data))
        mock_redis.delete = AsyncMock(return_value=1)

        # Mock session cookie
        response = await async_client.post(
            "/auth/logout", cookies={"session": "test_session_token"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Logout successful"

    @pytest.mark.asyncio
    async def test_logout_session_not_authenticated(self, async_client):
        """Test logout without authentication"""
        response = await async_client.post("/auth/logout")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestUserInfo:
    """Test user information endpoints"""

    @patch("app.dependencies.verify_token")
    def test_read_users_me_jwt(
        self, mock_verify_token, client, valid_user_payload, auth_headers
    ):
        """Test getting user info with JWT token"""
        mock_verify_token.return_value = valid_user_payload

        response = client.get("/auth/me/jwt", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["username"] == "testuser"
        assert data["auth_method"] == "jwt"
        assert "user" in data["roles"]

    @pytest.mark.asyncio
    async def test_read_users_me_session(
        self, async_client, mock_redis, mock_session_data
    ):
        """Test getting user info with session"""
        mock_redis.get = AsyncMock(return_value=json.dumps(mock_session_data))

        response = await async_client.get(
            "/auth/me/session", cookies={"session": "test_session_token"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["username"] == "sessionuser"
        assert data["auth_method"] == "session"

    def test_read_users_me_no_auth(self, client):
        """Test getting user info without authentication"""
        response = client.get("/auth/me/jwt")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("app.dependencies.verify_token")
    def test_read_users_me_flexible_jwt(
        self, mock_verify_token, client, valid_user_payload, auth_headers
    ):
        """Test flexible authentication with JWT"""
        mock_verify_token.return_value = valid_user_payload

        response = client.get("/auth/me", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["username"] == "testuser"


class TestSessionManagement:
    """Test session management endpoints"""

    @pytest.mark.asyncio
    async def test_list_active_sessions(self, async_client, mock_redis):
        """Test listing active sessions"""
        mock_sessions = [
            {
                "token": "session1",
                "user": {"username": "user1"},
                "created_at": "2024-01-01T00:00:00Z",
                "expires_at": "2024-01-02T00:00:00Z",
                "ttl_seconds": 86400,
            }
        ]

        with patch(
            "app.services.redis_session.redis_session_manager.get_all_sessions",
            AsyncMock(return_value=mock_sessions),
        ):
            response = await async_client.get("/auth/sessions")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["active_sessions"] == 1
            assert len(data["sessions"]) == 1

    @pytest.mark.asyncio
    async def test_clear_all_sessions(self, async_client):
        """Test clearing all sessions"""
        with patch(
            "app.services.redis_session.redis_session_manager.clear_all_sessions",
            AsyncMock(return_value=5),
        ):
            response = await async_client.delete("/auth/sessions")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "Cleared 5 active sessions" in data["message"]


class TestWebPages:
    """Test web page endpoints"""

    def test_login_page_not_authenticated(self, client):
        """Test login page when not authenticated"""
        response = client.get("/auth/login-page")

        assert response.status_code == status.HTTP_200_OK
        assert "text/html" in response.headers["content-type"]

    @patch("app.dependencies.verify_token")
    def test_login_page_already_authenticated(
        self, mock_verify_token, client, valid_user_payload, auth_headers
    ):
        """Test login page redirect when already authenticated"""
        mock_verify_token.return_value = valid_user_payload

        response = client.get("/auth/login-page", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        # Should redirect to dashboard

    def test_dashboard_page_not_authenticated(self, client):
        """Test dashboard page when not authenticated"""
        response = client.get("/auth/dashboard")

        assert response.status_code == status.HTTP_200_OK
        # Should redirect to login

    @patch("app.dependencies.verify_token")
    def test_dashboard_page_authenticated(
        self, mock_verify_token, client, valid_user_payload, auth_headers
    ):
        """Test dashboard page when authenticated"""
        mock_verify_token.return_value = valid_user_payload

        response = client.get("/auth/dashboard", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        assert "text/html" in response.headers["content-type"]


class TestOIDCAuthentication:
    """Test OIDC authentication flow"""

    @pytest.mark.asyncio
    async def test_oidc_login_disabled(self, async_client):
        """Test OIDC login when disabled"""
        with patch("config.config.settings.enable_oidc_login", False):
            response = await async_client.get("/auth/oidc/login")

            assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_oidc_login_success(
        self, async_client, mock_oidc_discovery, mock_redis
    ):
        """Test OIDC login initiation"""
        mock_redis.set = AsyncMock(return_value=True)

        with patch(
            "app.dependencies.get_oidc_discovery",
            AsyncMock(return_value=mock_oidc_discovery),
        ):
            response = await async_client.get("/auth/oidc/login")

            assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
            assert "oidc_session" in response.cookies
            assert "authorization_endpoint" in str(response.headers.get("location", ""))

    @pytest.mark.asyncio
    async def test_oidc_callback_missing_code(self, async_client):
        """Test OIDC callback without authorization code"""
        response = await async_client.get("/auth/oidc/callback?state=test_state")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Authorization code not provided" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_oidc_callback_missing_state(self, async_client):
        """Test OIDC callback without state parameter"""
        response = await async_client.get("/auth/oidc/callback?code=test_code")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "State parameter not provided" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_oidc_callback_error(self, async_client):
        """Test OIDC callback with error"""
        response = await async_client.get("/auth/oidc/callback?error=access_denied")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "OIDC authentication error" in response.json()["detail"]


class TestRootRedirect:
    """Test root redirect functionality"""

    def test_root_redirect_not_authenticated(self, client):
        """Test root redirect when not authenticated"""
        response = client.get("/auth/")

        assert response.status_code == status.HTTP_200_OK
        # Should redirect to login page

    @patch("app.dependencies.verify_token")
    def test_root_redirect_authenticated(
        self, mock_verify_token, client, valid_user_payload, auth_headers
    ):
        """Test root redirect when authenticated"""
        mock_verify_token.return_value = valid_user_payload

        response = client.get("/auth/", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        # Should redirect to dashboard


class TestAuthenticationHelpers:
    """Test authentication helper functions"""

    @patch(
        "app.services.users_roles_service.get_mock_users",
        return_value={
            "testuser": {
                "user_id": "1",
                "username": "testuser",
                "password": "testpass",
                "roles": ["user"],
            },
            "admin": {
                "user_id": "2",
                "username": "admin",
                "password": "admin123",
                "roles": ["admin", "user"],
            },
        },
    )
    def test_authenticate_user_valid(self, mock_get_users):
        """Test user authentication with valid credentials"""
        from app.routers.auth import authenticate_user

        user = authenticate_user("testuser", "testpass")
        assert user is not None
        assert user["username"] == "testuser"

    @patch(
        "app.services.users_roles_service.get_mock_users",
        return_value={
            "testuser": {
                "user_id": "1",
                "username": "testuser",
                "password": "testpass",
                "roles": ["user"],
            },
        },
    )
    def test_authenticate_user_invalid_username(self, mock_get_users):
        """Test user authentication with invalid username"""
        from app.routers.auth import authenticate_user

        user = authenticate_user("nonexistent", "testpass")
        assert user is None

    @patch(
        "app.services.users_roles_service.get_mock_users",
        return_value={
            "testuser": {
                "user_id": "1",
                "username": "testuser",
                "password": "testpass",
                "roles": ["user"],
            },
        },
    )
    def test_authenticate_user_invalid_password(self, mock_get_users):
        """Test user authentication with invalid password"""
        from app.routers.auth import authenticate_user

        user = authenticate_user("testuser", "wrongpass")
        assert user is None
