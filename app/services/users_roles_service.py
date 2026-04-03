from typing import Dict, Any, List, Optional
from pathlib import Path
import yaml
import logging

logger = logging.getLogger(__name__)

# Global users/roles configuration storage
_users_roles_config: Dict[str, Any] = {}


def _find_project_root() -> Path:
    """Find the project root directory by looking for requirements.txt"""
    current_path = Path(__file__).resolve()
    for parent in current_path.parents:
        if (parent / "requirements.txt").exists():
            return parent
    return current_path.parent.parent.parent


def load_users_roles_config() -> Dict[str, Any]:
    """Load users/roles configuration from YAML file"""
    project_root = _find_project_root()
    config_path = project_root / "config" / "users_roles_config.yaml"

    try:
        with open(config_path, "r", encoding="utf-8") as file:
            config = yaml.safe_load(file)
            return config or {}
    except FileNotFoundError:
        logger.warning(f"Users/roles config file not found at {config_path}")
        return {}
    except yaml.YAMLError as e:
        logger.error(f"Error parsing users/roles config YAML: {e}")
        return {}


def init_users_roles_config():
    """Initialize users/roles configuration on startup"""
    global _users_roles_config
    _users_roles_config = load_users_roles_config()
    role_mapping = _users_roles_config.get("oidc_role_mapping") or {}
    mock_users = _users_roles_config.get("mock_users") or {}
    menu_vis = _users_roles_config.get("menu_visibility") or {}
    logger.info(
        f"Loaded users/roles config: {len(role_mapping)} role(s), "
        f"{len(mock_users)} mock user(s), {len(menu_vis)} menu visibility rule(s)"
    )


def get_oidc_role_mapping() -> Dict[str, List[str]]:
    """Get OIDC role mapping (role name -> list of usernames)"""
    return _users_roles_config.get("oidc_role_mapping") or {}


def get_mock_users() -> Dict[str, Dict[str, Any]]:
    """Get mock user database"""
    return _users_roles_config.get("mock_users") or {}


def get_menu_visibility() -> Dict[str, List[str]]:
    """Get menu visibility configuration (menu_id -> list of allowed roles)"""
    return _users_roles_config.get("menu_visibility") or {}
