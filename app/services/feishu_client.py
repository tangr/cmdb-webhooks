"""
Feishu API client for approval operations.

This client handles:
- Tenant access token management (auto-refresh)
- Approval instance creation
- Approval status retrieval
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import httpx
import yaml

logger = logging.getLogger(__name__)


class FeishuClientConfig:
    """Configuration loader for Feishu client"""

    _config: Optional[Dict[str, Any]] = None
    _config_path: str = "config/feishu_approval_config.yaml"

    @classmethod
    def load_config(cls) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if cls._config is None:
            try:
                with open(cls._config_path, "r", encoding="utf-8") as f:
                    cls._config = yaml.safe_load(f)
            except FileNotFoundError:
                logger.error(f"Config file not found: {cls._config_path}")
                cls._config = {}
            except yaml.YAMLError as e:
                logger.error(f"Failed to parse config file: {e}")
                cls._config = {}
        return cls._config

    @classmethod
    def get_app_config(cls, app_name: str) -> Optional[Dict[str, str]]:
        """Get configuration for a specific app"""
        config = cls.load_config()
        apps = config.get("apps", {})
        return apps.get(app_name)

    @classmethod
    def get_global_config(cls) -> Dict[str, Any]:
        """Get global configuration"""
        config = cls.load_config()
        return {
            "base_url": config.get("feishu_base_url", "https://open.feishu.cn"),
            "timeout": config.get("feishu_timeout", 30),
            "token_expire_buffer": config.get("feishu_token_expire_buffer", 300),
        }

    @classmethod
    def reload_config(cls):
        """Force reload configuration"""
        cls._config = None
        cls.load_config()


class FeishuClient:
    """Feishu API client for approval operations"""

    # Class-level token cache: {app_name: {"token": str, "expires_at": datetime}}
    _token_cache: Dict[str, Dict[str, Any]] = {}

    def __init__(self, app_name: str):
        """
        Initialize Feishu client for a specific app.

        Args:
            app_name: The app name defined in feishu_approval_config.yaml
        """
        self.app_name = app_name

        # Load global config
        global_config = FeishuClientConfig.get_global_config()
        self.base_url = global_config["base_url"]
        self.timeout = global_config["timeout"]
        self.token_expire_buffer = global_config["token_expire_buffer"]

        # Load app config
        app_config = FeishuClientConfig.get_app_config(app_name)
        if not app_config:
            raise ValueError(f"App config not found for: {app_name}")

        self.app_id = app_config.get("app_id")
        self.app_secret = app_config.get("app_secret")
        self.default_approval_code = app_config.get("approval_code")

        if not self.app_id or not self.app_secret:
            raise ValueError(f"Missing app_id or app_secret for app: {app_name}")

    async def _get_access_token(self) -> str:
        """
        Get or refresh tenant access token.

        Uses class-level cache to avoid unnecessary API calls.
        Token is refreshed before expiration (based on token_expire_buffer).
        """
        cache_key = self.app_name
        cached = self._token_cache.get(cache_key)

        # Check if cached token is still valid
        if cached:
            expires_at = cached.get("expires_at")
            if expires_at and datetime.now() < expires_at - timedelta(
                seconds=self.token_expire_buffer
            ):
                return cached["token"]

        # Get new token from Feishu API
        url = f"{self.base_url}/open-apis/auth/v3/tenant_access_token/internal"
        data = {"app_id": self.app_id, "app_secret": self.app_secret}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=data)

            try:
                result = response.json()
            except Exception as e:
                raise Exception(
                    f"Failed to parse token response: {response.text}, error: {e}"
                )

            if response.status_code != 200:
                raise Exception(
                    f"Token API returned status {response.status_code}: {result}"
                )

            if result.get("code") != 0:
                raise Exception(f"Token API error: {result}")

            token = result.get("tenant_access_token")
            expires_in = int(result.get("expire", 7200))

            # Cache the token
            self._token_cache[cache_key] = {
                "token": token,
                "expires_at": datetime.now() + timedelta(seconds=expires_in),
            }

            logger.debug(f"Obtained new access token for app: {self.app_name}")
            return token

    async def create_approval_instance(
        self,
        user_id: str,
        form_data: Dict[str, Any],
        approval_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create an approval instance in Feishu.

        Args:
            user_id: Feishu user ID (short format, not open_id)
            form_data: Form data as key-value pairs
            approval_code: Approval definition code (uses default if not provided)

        Returns:
            Dict containing instance_code and other response data
        """
        token = await self._get_access_token()

        url = f"{self.base_url}/open-apis/approval/v4/instances"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        # Use provided approval_code or default from config
        code = approval_code or self.default_approval_code
        if not code:
            raise ValueError(
                f"No approval_code provided and no default configured for app: {self.app_name}"
            )

        # Convert form_data to Feishu format
        # Feishu expects: [{"id": "widget_id", "type": "type", "value": "value"}, ...]
        form_controls = []
        for key, value in form_data.items():
            form_controls.append(
                {
                    "id": key,
                    "type": "textarea",  # Default to textarea, can be extended
                    "value": str(value) if not isinstance(value, str) else value,
                }
            )

        request_data = {
            "approval_code": code,
            "user_id": user_id,
            "form": json.dumps(form_controls),
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, headers=headers, json=request_data)

            try:
                result = response.json()
            except Exception as e:
                raise Exception(
                    f"Failed to parse create approval response: {response.text}, error: {e}"
                )

            if response.status_code != 200:
                raise Exception(
                    f"Create approval API returned status {response.status_code}: {result}"
                )

            if result.get("code") != 0:
                raise Exception(f"Create approval API error: {result}")

            data = result.get("data", {})
            instance_code = data.get("instance_code")
            if not instance_code:
                raise Exception(f"No instance_code in response: {result}")

            logger.info(
                f"Created approval instance: {instance_code} for app: {self.app_name}"
            )
            return {
                "instance_code": instance_code,
                "raw_response": result,
            }

    async def get_approval_instance(self, instance_code: str) -> Dict[str, Any]:
        """
        Get approval instance details and status.

        Args:
            instance_code: Feishu approval instance code

        Returns:
            Dict containing approval status and details
        """
        token = await self._get_access_token()

        url = f"{self.base_url}/open-apis/approval/v4/instances/{instance_code}"
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, headers=headers)

            try:
                result = response.json()
            except Exception as e:
                raise Exception(
                    f"Failed to parse get approval response: {response.text}, error: {e}"
                )

            if response.status_code != 200:
                raise Exception(
                    f"Get approval API returned status {response.status_code}: {result}"
                )

            if result.get("code") != 0:
                raise Exception(f"Get approval API error: {result}")

            data = result.get("data", {})
            status = data.get("status", "UNKNOWN")

            # Map Feishu status to internal status
            status_map = {
                "PENDING": "pending",
                "APPROVED": "approved",
                "REJECTED": "rejected",
                "CANCELED": "canceled",
                "DELETED": "deleted",
            }

            return {
                "instance_code": instance_code,
                "status": status_map.get(status, status.lower()),
                "feishu_status": status,
                "raw_response": result,
            }

    @classmethod
    def clear_token_cache(cls, app_name: Optional[str] = None):
        """
        Clear token cache.

        Args:
            app_name: Specific app to clear, or None to clear all
        """
        if app_name:
            cls._token_cache.pop(app_name, None)
        else:
            cls._token_cache.clear()
