from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlmodel import create_engine, Session
from typing import Generator, Dict, List, Any, Optional
import redis.asyncio as redis
import json
from datetime import datetime, timedelta


class Settings(BaseSettings):
    app_name: str = "Awesome API"

    database_url: str = "mysql+pymysql://root:mypassword@127.0.0.1/test2"
    database_echo: bool = True

    feishu_webhook_base_url: str = "https://open.feishu.cn/open-apis/bot/v2/hook/"

    # X-API-Key
    # Webhook Security Configuration - API Key based authentication (supports multiple keys for rotation)
    cmdb_webhook_api_keys: str = (
        "QNbl7W9Ez7hVkR44ja93"  # Comma-separated API keys for CMDB webhook verification (empty = no verification)
    )
    feishu_webhook_api_keys: str = (
        ""  # Comma-separated API keys for Feishu webhook verification (empty = no verification)
    )
    webhook_ip_whitelist: List[str] = [
        "0.0.0.0/0",
        # IP Whitelist for webhook requests (empty list = deny all)
        # Examples:
        # "192.168.1.100",        # Single IP address
        # "10.0.0.0/8",          # CIDR block for entire 10.x.x.x network
        # "172.16.0.0/12",       # CIDR block for 172.16.x.x - 172.31.x.x
        # "127.0.0.1",           # Localhost
        # "::1",                 # IPv6 localhost
        # "0.0.0.0/0",           # Allow all IPv4 (equivalent to disabling IP restriction)
        # "::/0",                # Allow all IPv6 (equivalent to disabling IP restriction)
    ]

    # OIDC Configuration
    oidc_issuer_url: str = "https://sso-test.exodushk.com"
    oidc_client_id: str = "mytest-oidc"
    oidc_client_secret: str = "d5363c0d0bf650873176"
    oidc_redirect_uri: str = "http://localhost:8000/auth/oidc/callback"
    oidc_scope: str = "openid profile email"
    oidc_username_attribute: str = "preferred_username"
    oidc_login_button_text: str = "Sign in with OIDC"

    # Login Options Configuration
    # Enable/disable username/password login form
    enable_username_password_login: bool = True
    # Enable/disable OIDC login button
    enable_oidc_login: bool = True

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
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_to_file: bool = False
    # log_file_path: str = "/var/log/webhook-proxy/app.log"
    log_max_bytes: int = 10485760  # 10MB
    log_backup_count: int = 5
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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",  # Allow extra environment variables
    )


settings = Settings()

engine = create_engine(settings.database_url, echo=settings.database_echo)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
