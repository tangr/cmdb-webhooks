"""
Centralized Jinja2 template setup.

Provides a shared template factory with common filters and global functions
so that all routers use the same configuration.
"""

from fastapi.templating import Jinja2Templates
from app.utils.template_filters import time_to_str, time_diff_now
from config.config import settings
from typing import Optional


def _can_see_menu(user: Optional[object], menu_id: str) -> bool:
    """
    Check if a user can see a menu item based on configured role list.

    Args:
        user: User object with .roles attribute, or None if not authenticated.
        menu_id: The menu identifier to check (must exist in settings.menu_visibility).

    Returns:
        True if user has a matching role; False otherwise.
    """
    if user is None:
        return False

    allowed_roles = settings.menu_visibility.get(menu_id)
    if not allowed_roles:
        return False

    return any(role in user.roles for role in allowed_roles)


def create_templates() -> Jinja2Templates:
    """
    Create and configure a Jinja2Templates instance with shared filters and globals.
    """
    templates = Jinja2Templates(directory="templates")

    # Register filters
    templates.env.filters["timeToStr"] = time_to_str
    templates.env.filters["timeDiffNow"] = time_diff_now

    # Register global functions
    templates.env.globals["can_see_menu"] = _can_see_menu

    return templates
