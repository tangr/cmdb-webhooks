import base64
import secrets
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from fastapi.security.utils import get_authorization_scheme_param
from starlette.requests import Request

from app.services.vecmdb_trigger_service import get_prometheus_sd_configs
from app.utils.logger import get_logger

logger = get_logger(__name__)


def get_http_config_for_endpoint(config_name: str) -> Optional[Dict[str, Any]]:
    """Get HTTP config for a specific prometheus config"""
    configs = get_prometheus_sd_configs()
    prometheus_config = configs.get(config_name, {})
    http_config = prometheus_config.get("http_config")

    if not http_config or not isinstance(http_config, dict):
        return None

    return http_config


async def verify_basic_auth(
    username: str, password: str, config_name: str
) -> bool:
    """Verify HTTP Basic authentication credentials"""

    http_config = get_http_config_for_endpoint(config_name)
    basic_auth = (http_config or {}).get("basic_auth")
    if not basic_auth:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Basic"},
        )

    expected_username = basic_auth.get("username")
    expected_password = basic_auth.get("password")

    # Load from file if specified
    if basic_auth.get("username_file"):
        try:
            with open(basic_auth["username_file"], "r") as f:
                expected_username = f.read().strip()
        except Exception as e:
            logger.error(f"Failed to read username file: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    if basic_auth.get("password_file"):
        try:
            with open(basic_auth["password_file"], "r") as f:
                expected_password = f.read().strip()
        except Exception as e:
            logger.error(f"Failed to read password file: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    if not expected_username or not expected_password:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication configuration incomplete",
        )

    # Use constant time comparison to prevent timing attacks
    correct_username = secrets.compare_digest(username, expected_username)
    correct_password = secrets.compare_digest(password, expected_password)

    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    return True


async def verify_bearer_auth(token: str, config_name: str) -> bool:
    """Verify Bearer token authentication"""

    http_config = get_http_config_for_endpoint(config_name)
    authorization = (http_config or {}).get("authorization")
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    expected_token = authorization.get("credentials")

    # Load from file if specified
    if authorization.get("credentials_file"):
        try:
            with open(authorization["credentials_file"], "r") as f:
                expected_token = f.read().strip()
        except Exception as e:
            logger.error(f"Failed to read credentials file: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    if not expected_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication configuration incomplete",
        )

    # Verify token using constant time comparison
    if not secrets.compare_digest(token, expected_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return True


async def authenticate_request(
    request: Request, config_name: str = "default"
) -> bool:
    """Main authentication function that handles different auth types"""

    http_config = get_http_config_for_endpoint(config_name)
    if not http_config:
        # No authentication required for this endpoint
        return True

    authorization_header = request.headers.get("Authorization")
    if not authorization_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    scheme, credentials = get_authorization_scheme_param(authorization_header)

    # Handle Basic authentication
    if http_config.get("basic_auth") and scheme.lower() == "basic":
        try:
            decoded = base64.b64decode(credentials).decode("utf-8")
            username, password = decoded.split(":", 1)
            await verify_basic_auth(username, password, config_name)
            return True
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Basic auth verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid basic authentication",
                headers={"WWW-Authenticate": "Basic"},
            )

    # Handle Bearer authentication
    elif http_config.get("authorization") and scheme.lower() == "bearer":
        try:
            await verify_bearer_auth(credentials, config_name)
            return True
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Bearer auth verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid bearer token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # No matching auth scheme
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication scheme",
    )
