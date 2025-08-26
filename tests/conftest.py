import pytest
import asyncio
from typing import Generator, AsyncGenerator
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session
from httpx import AsyncClient, ASGITransport
import redis.asyncio as redis

from app.main import app
from config.config import Settings, get_session


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings():
    """Create test settings with in-memory database"""
    return Settings(
        database_url="sqlite:///./test.db",
        database_echo=False,
        redis_host="localhost",
        redis_port=6379,
        redis_db=14,  # Different from production
        log_level="DEBUG",
        enable_console_logging=False,
        oidc_issuer_url="https://test-oidc.example.com",
        oidc_client_id="test-client",
        oidc_client_secret="test-secret",
        cmdb_webhook_api_keys="test-api-key",
        feishu_webhook_api_keys="",
    )


@pytest.fixture(scope="session")
def test_engine(test_settings):
    """Create test database engine"""
    engine = create_engine(
        test_settings.database_url,
        echo=test_settings.database_echo,
        connect_args={"check_same_thread": False},  # For SQLite
    )

    # Create all tables
    SQLModel.metadata.create_all(engine)

    yield engine

    # Clean up
    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def test_session(test_engine) -> Generator[Session, None, None]:
    """Create a test database session with automatic cleanup"""
    with Session(test_engine) as session:
        yield session
        # Clean up after test - rollback any uncommitted changes
        session.rollback()
        # Clear all data from tables for next test
        for table in SQLModel.metadata.tables.values():
            session.execute(table.delete())
        session.commit()


@pytest.fixture
def override_get_session(test_session):
    """Override the get_session dependency"""

    def _override_get_session():
        yield test_session

    return _override_get_session


@pytest.fixture
def mock_redis():
    """Mock Redis connection"""
    mock_redis = Mock()
    mock_redis.get = Mock(return_value=None)
    mock_redis.set = Mock(return_value=True)
    mock_redis.delete = Mock(return_value=1)
    mock_redis.exists = Mock(return_value=False)
    mock_redis.expire = Mock(return_value=True)
    return mock_redis


@pytest.fixture
def client(override_get_session, mock_redis, test_settings):
    """Create test client with mocked dependencies"""
    # Override dependencies
    app.dependency_overrides[get_session] = override_get_session

    # Mock settings
    with patch("config.config.settings", test_settings):
        # Mock Redis
        with patch(
            "app.services.redis_session.get_redis_connection", return_value=mock_redis
        ):
            # Mock webhook mapping initialization
            with patch("app.services.webhook_mapping.init_webhook_mapping"):
                # Mock logging setup
                with patch("app.utils.logger.setup_logging"):
                    with TestClient(app) as test_client:
                        yield test_client

    # Clean up overrides
    app.dependency_overrides.clear()


@pytest.fixture
async def async_client(override_get_session, mock_redis, test_settings):
    """Create async test client"""
    # Override dependencies
    app.dependency_overrides[get_session] = override_get_session

    # Mock settings
    with patch("config.config.settings", test_settings):
        # Mock Redis
        with patch(
            "app.services.redis_session.get_redis_connection", return_value=mock_redis
        ):
            # Mock webhook mapping initialization
            with patch("app.services.webhook_mapping.init_webhook_mapping"):
                # Mock logging setup
                with patch("app.utils.logger.setup_logging"):
                    transport = ASGITransport(app=app)
                    async with AsyncClient(
                        transport=transport, base_url="http://test"
                    ) as ac:
                        yield ac

    # Clean up overrides
    app.dependency_overrides.clear()


@pytest.fixture
def mock_jwt_token():
    """Create a mock JWT token for testing"""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0X3VzZXJfaWQiLCJ1c2VybmFtZSI6InRlc3R1c2VyIiwicm9sZXMiOlsidXNlciJdLCJleHAiOjk5OTk5OTk5OTl9.mock_signature"


@pytest.fixture
def mock_admin_jwt_token():
    """Create a mock admin JWT token for testing"""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbl91c2VyX2lkIiwidXNlcm5hbWUiOiJhZG1pbiIsInJvbGVzIjpbImFkbWluIiwidXNlciJdLCJleHAiOjk5OTk5OTk5OTl9.mock_signature"


@pytest.fixture
def valid_user_payload():
    """User payload for JWT token"""
    return {"user_id": "test_user_id", "username": "testuser", "roles": ["user"]}


@pytest.fixture
def valid_admin_payload():
    """Admin user payload for JWT token"""
    return {"user_id": "admin_user_id", "username": "admin", "roles": ["admin", "user"]}


@pytest.fixture
def mock_session_data():
    """Mock session data for Redis"""
    return {
        "user_id": "session_user_id",
        "username": "sessionuser",
        "roles": ["user"],
        "created_at": "2024-01-01T00:00:00Z",
    }


@pytest.fixture
def mock_oidc_discovery():
    """Mock OIDC discovery document"""
    return {
        "issuer": "https://test-oidc.example.com",
        "authorization_endpoint": "https://test-oidc.example.com/auth",
        "token_endpoint": "https://test-oidc.example.com/token",
        "userinfo_endpoint": "https://test-oidc.example.com/userinfo",
        "jwks_uri": "https://test-oidc.example.com/.well-known/jwks.json",
    }


@pytest.fixture
def mock_oidc_jwks():
    """Mock OIDC JWKS response"""
    return {
        "keys": [
            {
                "kty": "RSA",
                "kid": "test-key-id",
                "use": "sig",
                "alg": "RS256",
                "n": "test-n-value",
                "e": "AQAB",
            }
        ]
    }


@pytest.fixture
def sample_cmdb_request():
    """Sample CMDB request data for testing"""
    return {
        "host": "http://127.0.0.1:8000",
        "method": "POST",
        "path": "/api/test",
        "query": "param1=value1&param2=value2",
        "headers": {"Content-Type": "application/json", "User-Agent": "curl/7.68.0"},
        "body": {"test_key": "test_value", "data": "sample data"},
        "author": "test_user",
        "clientip": "127.0.0.1",
        "status": 200,
        "output": "Success response",
    }


@pytest.fixture
def sample_feishu_webhook():
    """Sample Feishu webhook data for testing"""
    return {
        "status": "firing",
        "title": "[🔥:1] test-High CPU usage",
        "message": "Test alert message",
    }


@pytest.fixture
def auth_headers(mock_jwt_token):
    """Authorization headers with JWT token"""
    return {"Authorization": f"Bearer {mock_jwt_token}"}


@pytest.fixture
def admin_auth_headers(mock_admin_jwt_token):
    """Authorization headers with admin JWT token"""
    return {"Authorization": f"Bearer {mock_admin_jwt_token}"}


@pytest.fixture
def api_key_headers():
    """API key headers for webhook endpoints"""
    return {"X-API-Key": "test-api-key"}
