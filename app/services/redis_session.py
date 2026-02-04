import redis.asyncio as redis
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List
from config.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RedisSessionManager:
    """Redis-based session management"""

    def __init__(self):
        self._pool: Optional[redis.ConnectionPool] = None
        self._client: Optional[redis.Redis] = None

    def _get_pool(self) -> redis.ConnectionPool:
        """Get or create Redis connection pool"""
        if self._pool is None:
            logger.debug(
                f"Creating Redis connection pool for host: {settings.redis_host}, port: {settings.redis_port}, db: {settings.redis_db}, password: {'****' if settings.redis_password else '(none)'}"
            )
            self._pool = redis.ConnectionPool(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password if settings.redis_password else None,
                decode_responses=settings.redis_decode_responses,
                max_connections=settings.redis_max_connections,
            )
        return self._pool

    def _get_client(self) -> redis.Redis:
        """Get Redis client from connection pool"""
        if self._client is None:
            self._client = redis.Redis(connection_pool=self._get_pool())
        return self._client

    def create_session_token(self) -> str:
        """Create secure session token"""
        return secrets.token_urlsafe(32)

    async def set_session(
        self, session_token: str, user_data: Dict, expire_seconds: int = None
    ) -> bool:
        """Store session data in Redis"""
        try:
            client = self._get_client()
            key = f"{settings.session_redis_key_prefix}{session_token}"

            # Add timestamp for tracking
            session_data = {
                "user": user_data,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": (
                    datetime.now(timezone.utc)
                    + timedelta(
                        seconds=expire_seconds or settings.session_expire_seconds
                    )
                ).isoformat(),
            }

            # Store session data with expiration
            expire_time = expire_seconds or settings.session_expire_seconds
            await client.setex(key, expire_time, json.dumps(session_data))
            return True
        except Exception as e:
            logger.error(f"Error setting session data: {e}")
            return False

    async def get_session(self, session_token: str) -> Optional[Dict]:
        """Retrieve session data from Redis"""
        try:
            client = self._get_client()
            key = f"{settings.session_redis_key_prefix}{session_token}"

            data = await client.get(key)
            if data:
                session_data = json.loads(data)
                return session_data.get("user")
            return None
        except Exception as e:
            logger.error(f"Error getting session data: {e}")
            return None

    async def delete_session(self, session_token: str) -> bool:
        """Delete session data from Redis"""
        try:
            client = self._get_client()
            key = f"{settings.session_redis_key_prefix}{session_token}"
            result = await client.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Error deleting session data: {e}")
            return False

    async def get_all_sessions(self) -> List[Dict]:
        """Get all active sessions (for admin purposes)"""
        try:
            client = self._get_client()
            pattern = f"{settings.session_redis_key_prefix}*"
            keys = await client.keys(pattern)

            sessions = []
            for key in keys:
                data = await client.get(key)
                if data:
                    session_data = json.loads(data)
                    ttl = await client.ttl(key)
                    sessions.append(
                        {
                            "token": key.replace(settings.session_redis_key_prefix, ""),
                            "user": session_data.get("user", {}),
                            "created_at": session_data.get("created_at"),
                            "expires_at": session_data.get("expires_at"),
                            "ttl_seconds": ttl,
                        }
                    )
            return sessions
        except Exception as e:
            logger.error(f"Error getting all sessions: {e}")
            return []

    async def clear_all_sessions(self) -> int:
        """Clear all active sessions (for admin purposes)"""
        try:
            client = self._get_client()
            pattern = f"{settings.session_redis_key_prefix}*"
            keys = await client.keys(pattern)
            if keys:
                result = await client.delete(*keys)
                return result
            return 0
        except Exception as e:
            logger.error(f"Error clearing all sessions: {e}")
            return 0


# Global session manager instance
redis_session_manager = RedisSessionManager()
