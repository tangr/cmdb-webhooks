import pytest
import json
import time
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta, timezone

from app.services.redis_session import RedisSessionManager, redis_session_manager


@pytest.mark.unit
@pytest.mark.redis
class TestRedisSessionManager:
    """Test Redis session manager functionality"""

    @pytest.fixture
    def session_manager(self):
        """Create a new RedisSessionManager instance for testing"""
        return RedisSessionManager()

    @pytest.fixture
    def mock_redis_client(self):
        """Mock Redis client"""
        mock_client = AsyncMock()
        mock_client.setex = AsyncMock(return_value=True)
        mock_client.get = AsyncMock(return_value=None)
        mock_client.delete = AsyncMock(return_value=1)
        mock_client.keys = AsyncMock(return_value=[])
        mock_client.ttl = AsyncMock(return_value=3600)
        return mock_client

    @pytest.fixture
    def sample_user_data(self):
        """Sample user data for testing"""
        return {
            "user_id": "user123",
            "username": "testuser",
            "roles": ["user"],
            "email": "test@example.com",
        }

    def test_create_session_token(self, session_manager):
        """Test session token creation"""
        token1 = session_manager.create_session_token()
        token2 = session_manager.create_session_token()

        assert isinstance(token1, str)
        assert isinstance(token2, str)
        assert len(token1) > 32  # URL-safe base64 encoding makes it longer
        assert len(token2) > 32
        assert token1 != token2  # Each token should be unique

    @pytest.mark.asyncio
    @patch("app.services.redis_session.redis.Redis")
    async def test_set_session_success(
        self, mock_redis_class, session_manager, mock_redis_client, sample_user_data
    ):
        """Test successful session creation"""
        mock_redis_class.return_value = mock_redis_client
        session_manager._client = mock_redis_client

        token = "test_session_token"
        result = await session_manager.set_session(
            token, sample_user_data, expire_seconds=3600
        )

        assert result is True
        mock_redis_client.setex.assert_called_once()

        # Check the key format
        call_args = mock_redis_client.setex.call_args
        key, expire_time, data = call_args[0]

        assert "session:" in key
        assert token in key
        assert expire_time == 3600

        # Check session data structure
        session_data = json.loads(data)
        assert "user" in session_data
        assert "created_at" in session_data
        assert "expires_at" in session_data
        assert session_data["user"] == sample_user_data

    @pytest.mark.asyncio
    @patch("app.services.redis_session.redis.Redis")
    async def test_set_session_with_default_expiry(
        self, mock_redis_class, session_manager, mock_redis_client, sample_user_data
    ):
        """Test session creation with default expiry time"""
        mock_redis_class.return_value = mock_redis_client
        session_manager._client = mock_redis_client

        with patch("config.config.settings.session_expire_seconds", 86400):  # 24 hours
            token = "test_token"
            result = await session_manager.set_session(token, sample_user_data)

            assert result is True
            call_args = mock_redis_client.setex.call_args
            key, expire_time, data = call_args[0]
            assert expire_time == 86400

    @pytest.mark.asyncio
    @patch("app.services.redis_session.redis.Redis")
    async def test_set_session_error(
        self, mock_redis_class, session_manager, sample_user_data
    ):
        """Test session creation with Redis error"""
        mock_client = AsyncMock()
        mock_client.setex = AsyncMock(side_effect=Exception("Redis connection error"))
        mock_redis_class.return_value = mock_client
        session_manager._client = mock_client

        token = "test_token"
        result = await session_manager.set_session(token, sample_user_data)

        assert result is False

    @pytest.mark.asyncio
    @patch("app.services.redis_session.redis.Redis")
    async def test_get_session_success(
        self, mock_redis_class, session_manager, mock_redis_client, sample_user_data
    ):
        """Test successful session retrieval"""
        session_data = {
            "user": sample_user_data,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        }

        mock_redis_client.get = AsyncMock(return_value=json.dumps(session_data))
        mock_redis_class.return_value = mock_redis_client
        session_manager._client = mock_redis_client

        token = "test_token"
        result = await session_manager.get_session(token)

        assert result == sample_user_data
        mock_redis_client.get.assert_called_once()

        # Check the key format
        call_args = mock_redis_client.get.call_args
        key = call_args[0][0]
        assert "session:" in key
        assert token in key

    @pytest.mark.asyncio
    @patch("app.services.redis_session.redis.Redis")
    async def test_get_session_not_found(
        self, mock_redis_class, session_manager, mock_redis_client
    ):
        """Test session retrieval when session doesn't exist"""
        mock_redis_client.get = AsyncMock(return_value=None)
        mock_redis_class.return_value = mock_redis_client
        session_manager._client = mock_redis_client

        token = "nonexistent_token"
        result = await session_manager.get_session(token)

        assert result is None

    @pytest.mark.asyncio
    @patch("app.services.redis_session.redis.Redis")
    async def test_get_session_error(self, mock_redis_class, session_manager):
        """Test session retrieval with Redis error"""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("Redis connection error"))
        mock_redis_class.return_value = mock_client
        session_manager._client = mock_client

        token = "test_token"
        result = await session_manager.get_session(token)

        assert result is None

    @pytest.mark.asyncio
    @patch("app.services.redis_session.redis.Redis")
    async def test_delete_session_success(
        self, mock_redis_class, session_manager, mock_redis_client
    ):
        """Test successful session deletion"""
        mock_redis_client.delete = AsyncMock(return_value=1)
        mock_redis_class.return_value = mock_redis_client
        session_manager._client = mock_redis_client

        token = "test_token"
        result = await session_manager.delete_session(token)

        assert result is True
        mock_redis_client.delete.assert_called_once()

        # Check the key format
        call_args = mock_redis_client.delete.call_args
        key = call_args[0][0]
        assert "session:" in key
        assert token in key

    @pytest.mark.asyncio
    @patch("app.services.redis_session.redis.Redis")
    async def test_delete_session_not_found(
        self, mock_redis_class, session_manager, mock_redis_client
    ):
        """Test session deletion when session doesn't exist"""
        mock_redis_client.delete = AsyncMock(return_value=0)
        mock_redis_class.return_value = mock_redis_client
        session_manager._client = mock_redis_client

        token = "nonexistent_token"
        result = await session_manager.delete_session(token)

        assert result is False

    @pytest.mark.asyncio
    @patch("app.services.redis_session.redis.Redis")
    async def test_delete_session_error(self, mock_redis_class, session_manager):
        """Test session deletion with Redis error"""
        mock_client = AsyncMock()
        mock_client.delete = AsyncMock(side_effect=Exception("Redis connection error"))
        mock_redis_class.return_value = mock_client
        session_manager._client = mock_client

        token = "test_token"
        result = await session_manager.delete_session(token)

        assert result is False

    @pytest.mark.asyncio
    @patch("app.services.redis_session.redis.Redis")
    async def test_get_all_sessions_success(
        self, mock_redis_class, session_manager, mock_redis_client, sample_user_data
    ):
        """Test retrieving all active sessions"""
        # Mock keys and session data
        session_keys = ["session:token1", "session:token2", "session:token3"]

        session_data_1 = {
            "user": sample_user_data,
            "created_at": "2024-01-01T10:00:00Z",
            "expires_at": "2024-01-01T11:00:00Z",
        }

        session_data_2 = {
            "user": {"user_id": "user456", "username": "admin", "roles": ["admin"]},
            "created_at": "2024-01-01T10:30:00Z",
            "expires_at": "2024-01-01T11:30:00Z",
        }

        mock_redis_client.keys = AsyncMock(return_value=session_keys)
        mock_redis_client.get = AsyncMock(
            side_effect=[
                json.dumps(session_data_1),
                json.dumps(session_data_2),
                None,  # Third key returns None (expired)
            ]
        )
        mock_redis_client.ttl = AsyncMock(side_effect=[3600, 1800, -1])

        mock_redis_class.return_value = mock_redis_client
        session_manager._client = mock_redis_client

        result = await session_manager.get_all_sessions()

        assert len(result) == 2  # Third session is None so not included

        # Check first session
        assert result[0]["token"] == "token1"
        assert result[0]["user"] == sample_user_data
        assert result[0]["created_at"] == "2024-01-01T10:00:00Z"
        assert result[0]["ttl_seconds"] == 3600

        # Check second session
        assert result[1]["token"] == "token2"
        assert result[1]["user"]["username"] == "admin"
        assert result[1]["ttl_seconds"] == 1800

    @pytest.mark.asyncio
    @patch("app.services.redis_session.redis.Redis")
    async def test_get_all_sessions_empty(
        self, mock_redis_class, session_manager, mock_redis_client
    ):
        """Test retrieving all sessions when none exist"""
        mock_redis_client.keys = AsyncMock(return_value=[])
        mock_redis_class.return_value = mock_redis_client
        session_manager._client = mock_redis_client

        result = await session_manager.get_all_sessions()

        assert result == []

    @pytest.mark.asyncio
    @patch("app.services.redis_session.redis.Redis")
    async def test_get_all_sessions_error(self, mock_redis_class, session_manager):
        """Test get all sessions with Redis error"""
        mock_client = AsyncMock()
        mock_client.keys = AsyncMock(side_effect=Exception("Redis connection error"))
        mock_redis_class.return_value = mock_client
        session_manager._client = mock_client

        result = await session_manager.get_all_sessions()

        assert result == []

    @pytest.mark.asyncio
    @patch("app.services.redis_session.redis.Redis")
    async def test_clear_all_sessions_success(
        self, mock_redis_class, session_manager, mock_redis_client
    ):
        """Test clearing all sessions successfully"""
        session_keys = ["session:token1", "session:token2", "session:token3"]

        mock_redis_client.keys = AsyncMock(return_value=session_keys)
        mock_redis_client.delete = AsyncMock(return_value=3)
        mock_redis_class.return_value = mock_redis_client
        session_manager._client = mock_redis_client

        result = await session_manager.clear_all_sessions()

        assert result == 3
        mock_redis_client.keys.assert_called_once()
        mock_redis_client.delete.assert_called_once_with(*session_keys)

    @pytest.mark.asyncio
    @patch("app.services.redis_session.redis.Redis")
    async def test_clear_all_sessions_empty(
        self, mock_redis_class, session_manager, mock_redis_client
    ):
        """Test clearing sessions when none exist"""
        mock_redis_client.keys = AsyncMock(return_value=[])
        mock_redis_class.return_value = mock_redis_client
        session_manager._client = mock_redis_client

        result = await session_manager.clear_all_sessions()

        assert result == 0
        mock_redis_client.keys.assert_called_once()
        mock_redis_client.delete.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.services.redis_session.redis.Redis")
    async def test_clear_all_sessions_error(self, mock_redis_class, session_manager):
        """Test clear all sessions with Redis error"""
        mock_client = AsyncMock()
        mock_client.keys = AsyncMock(side_effect=Exception("Redis connection error"))
        mock_redis_class.return_value = mock_client
        session_manager._client = mock_client

        result = await session_manager.clear_all_sessions()

        assert result == 0

    def test_connection_pool_creation(self, session_manager):
        """Test Redis connection pool creation"""
        with patch("config.config.settings.redis_host", "test-host"):
            with patch("config.config.settings.redis_port", 6380):
                with patch("config.config.settings.redis_db", 15):
                    with patch(
                        "app.services.redis_session.redis.ConnectionPool"
                    ) as mock_pool:
                        pool = session_manager._get_pool()

                        mock_pool.assert_called_once_with(
                            host="test-host",
                            port=6380,
                            db=15,
                            password=None,
                            decode_responses=True,
                            max_connections=10,
                        )

    def test_global_session_manager(self):
        """Test that global session manager instance exists"""
        assert redis_session_manager is not None
        assert isinstance(redis_session_manager, RedisSessionManager)
