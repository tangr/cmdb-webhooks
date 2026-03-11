from typing import Dict, Any, Optional, List
from pathlib import Path
from urllib.parse import quote
import yaml
import httpx
import base64
from datetime import datetime
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Global configuration storage
_harbor_config: Dict[str, Any] = {}


def _find_project_root() -> Path:
    """Find the project root directory by looking for requirements.txt"""
    current_path = Path(__file__).resolve()
    for parent in current_path.parents:
        if (parent / "requirements.txt").exists():
            return parent
    return current_path.parent.parent.parent


def load_harbor_config() -> Dict[str, Any]:
    """Load Harbor configuration from YAML file"""
    project_root = _find_project_root()
    config_path = project_root / "config" / "harbor_config.yaml"

    try:
        with open(config_path, "r", encoding="utf-8") as file:
            config = yaml.safe_load(file)
            return config or {}
    except FileNotFoundError:
        logger.warning(f"Harbor config file not found at {config_path}")
        return {}
    except yaml.YAMLError as e:
        logger.error(f"Error parsing Harbor config YAML: {e}")
        return {}


def init_harbor_config():
    """Initialize Harbor configuration on startup"""
    global _harbor_config
    _harbor_config = load_harbor_config()
    instances = _harbor_config.get("instances") or {}
    logger.info(f"Loaded {len(instances)} Harbor instances")


def get_harbor_config() -> Dict[str, Any]:
    """Get the current Harbor configuration"""
    return _harbor_config


def get_harbor_instance(instance_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get Harbor instance configuration by ID.

    Args:
        instance_id: Instance identifier (e.g., "prod", "dev").
                    If None, uses default_instance from config.

    Returns:
        Instance configuration dict or None if not found
    """
    if not instance_id:
        instance_id = _harbor_config.get("default_instance", "")

    if not instance_id:
        return None

    instances = _harbor_config.get("instances") or {}
    return instances.get(instance_id)


def get_default_page_size() -> int:
    """Get default page size from config"""
    return _harbor_config.get("default_page_size", 50)


def get_max_page_size() -> int:
    """Get max page size from config"""
    return _harbor_config.get("max_page_size", 100)


def get_default_timeout() -> int:
    """Get default timeout from config"""
    return _harbor_config.get("default_timeout", 30)


def _build_auth_header(robot_token: str) -> str:
    """
    Build Basic Auth header from robot token.

    Harbor Robot Token format: robot$<name>:<secret>
    Auth header format: Basic base64(<name>:<secret>)
    """
    # Robot token is already in username:password format
    encoded = base64.b64encode(robot_token.encode("utf-8")).decode("utf-8")
    return f"Basic {encoded}"


def _format_push_time(push_time_str: str) -> str:
    """
    Format push time string for display.

    Args:
        push_time_str: ISO format datetime string (e.g., "2024-03-10T14:30:00.000Z")

    Returns:
        Formatted string (e.g., "2024-03-10 14:30")
    """
    try:
        # Parse ISO format datetime
        dt = datetime.fromisoformat(push_time_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, AttributeError):
        return push_time_str[:16] if push_time_str else ""


def _get_digest_short(digest: str) -> str:
    """
    Get shortened digest for display.

    Args:
        digest: Full digest string (e.g., "sha256:abc123...")

    Returns:
        Shortened digest (e.g., "sha256:abc123")
    """
    if digest and ":" in digest:
        prefix, hash_value = digest.split(":", 1)
        return f"{prefix}:{hash_value[:12]}"
    return digest[:20] if digest else ""


async def fetch_artifacts(
    instance_id: Optional[str],
    project: str,
    repo: str,
    page: int = 1,
    page_size: int = 50,
) -> Dict[str, Any]:
    """
    Fetch artifacts from Harbor API.

    Args:
        instance_id: Harbor instance identifier
        project: Project name
        repo: Repository name
        page: Page number (1-based)
        page_size: Number of items per page

    Returns:
        Dict with artifacts data and pagination info
    """
    # Get instance configuration
    instance = get_harbor_instance(instance_id)
    if not instance:
        available = list((_harbor_config.get("instances") or {}).keys())
        return {
            "error": f"Harbor instance '{instance_id or 'default'}' not found",
            "available_instances": available,
        }

    base_url = instance.get("base_url", "").rstrip("/")
    robot_token = instance.get("robot_token", "")
    timeout = instance.get("timeout", get_default_timeout())

    if not base_url:
        return {"error": "Harbor base_url not configured for this instance"}

    if not robot_token:
        return {"error": "Harbor robot_token not configured for this instance"}

    # Validate and cap page_size
    max_size = get_max_page_size()
    if page_size > max_size:
        page_size = max_size

    # Build Harbor API URL
    # Harbor API v2.0: /api/v2.0/projects/{project_name}/repositories/{repository_name}/artifacts
    # Repository name must be URL encoded (e.g., "qa/ipip-service" -> "qa%2Fipip-service")
    repo_encoded = quote(repo, safe="")
    api_url = f"{base_url}/api/v2.0/projects/{project}/repositories/{repo_encoded}/artifacts"

    # Query parameters
    params = {
        "page": page,
        "page_size": page_size,
        "with_tag": "true",  # Include tag information
    }

    # Build headers
    headers = {
        "Authorization": _build_auth_header(robot_token),
        "Accept": "application/json",
    }

    logger.debug(f"Fetching Harbor artifacts: {api_url}")

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(api_url, params=params, headers=headers)

            # Log response status
            logger.debug(f"Harbor API response status: {response.status_code}")

            if response.status_code == 401:
                return {"error": "Harbor authentication failed - check robot token"}

            if response.status_code == 403:
                return {"error": "Harbor access denied - robot lacks permission"}

            if response.status_code == 404:
                return {
                    "error": f"Project '{project}' or repository '{repo}' not found"
                }

            response.raise_for_status()

            artifacts = response.json()

            # Get total count from response header if available
            total_count = response.headers.get("X-Total-Count")
            has_more = len(artifacts) >= page_size

            return {
                "artifacts": artifacts,
                "page": page,
                "page_size": page_size,
                "has_more": has_more,
                "total_count": int(total_count) if total_count else None,
            }

    except httpx.TimeoutException:
        logger.error(f"Harbor API timeout: {api_url}")
        return {"error": "Harbor API request timed out"}

    except httpx.RequestError as e:
        logger.error(f"Harbor API request error: {e}")
        return {"error": f"Failed to connect to Harbor: {str(e)}"}

    except Exception as e:
        logger.error(f"Harbor API unexpected error: {e}")
        return {"error": f"Unexpected error: {str(e)}"}


def format_artifacts_for_amis(
    artifacts: List[Dict[str, Any]], project: str, repo: str
) -> List[Dict[str, str]]:
    """
    Format Harbor artifacts for Amis select input options.

    Args:
        artifacts: List of artifact data from Harbor API
        project: Project name
        repo: Repository name

    Returns:
        List of options with 'label' and 'value' keys
    """
    options = []

    for artifact in artifacts:
        digest = artifact.get("digest", "")
        push_time = artifact.get("push_time", "")
        tags = artifact.get("tags") or []

        formatted_time = _format_push_time(push_time)

        if tags:
            # Artifact has tags - create option for each tag
            for tag in tags:
                tag_name = tag.get("name", "")
                tag_push_time = tag.get("push_time", push_time)
                tag_formatted_time = _format_push_time(tag_push_time)

                if tag_name:
                    options.append(
                        {
                            "label": f"{tag_name} ({tag_formatted_time})",
                            "value": f"{project}/{repo}:{tag_name}",
                        }
                    )
        else:
            # No tags - use digest
            digest_short = _get_digest_short(digest)
            options.append(
                {
                    "label": f"{digest_short} ({formatted_time})",
                    "value": f"{project}/{repo}@{digest}",
                }
            )

    return options
