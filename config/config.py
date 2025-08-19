from pydantic_settings import BaseSettings
from sqlmodel import create_engine, Session
from typing import Generator, Dict, List, Any, Optional
import redis.asyncio as redis
import json
from datetime import datetime, timedelta


class Settings(BaseSettings):
    app_name: str = "Awesome API"
    admin_email: str
    items_per_user: int = 50

    database_url: str = "mysql+pymysql://root:mypassword@127.0.0.1/test2"
    database_echo: bool = True

    feishu_webhook_base_url: str = "https://open.feishu.cn/open-apis/bot/v2/hook/"

    # OIDC Configuration
    oidc_issuer_url: str = "https://sso-test.exodushk.com"
    oidc_client_id: str = "mytest-oidc"
    oidc_client_secret: str = "d5363c0d0bf650873176"
    oidc_redirect_uri: str = "http://localhost:8000/auth/oidc/callback"
    oidc_scope: str = "openid profile email"
    oidc_username_attribute: str = "preferred_username"

    # Redis Configuration for Session Storage
    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    redis_db: int = 13
    redis_password: str = ""
    redis_max_connections: int = 10
    redis_decode_responses: bool = True
    session_redis_key_prefix: str = "session:"
    session_expire_seconds: int = 86400  # 24 hours

    # Logging configuration
    enable_database_logging: bool = True
    enable_console_logging: bool = False

    # Role mapping configuration for OIDC users
    # Map usernames to roles - users not in any list get default "user" role
    oidc_role_mapping: Dict[str, List[str]] = {
        "admin": [
            # Add admin usernames here
            "admin@example.com",
            "administrator",
            "root",
            "tangshoubin",
        ],
        "user": [
            # Add regular user usernames here (optional, as "user" is default)
            # "user@example.com",
        ],
    }

    # Mock user database configuration
    mock_users: Dict[str, Dict[str, Any]] = {
        "testuser": {
            "user_id": "1",
            "username": "testuser",
            "password": "testpass",  # In production, use hashed passwords
            "roles": ["user"],
        },
        "admin": {
            "user_id": "2",
            "username": "admin",
            "password": "admin123",
            "roles": ["admin", "user"],
        },
    }

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()

engine = create_engine(settings.database_url, echo=settings.database_echo)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
