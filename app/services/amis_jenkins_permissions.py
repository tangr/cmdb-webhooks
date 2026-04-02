"""
Form-level permission checking for Amis Jenkins module.

Permission model:
- admin role bypasses all checks
- No permissions block in form config = admin-only
- allowed_roles / allowed_users: can view + submit + view history
- execute_roles / execute_users + submitter + admin: can execute pending jobs
"""

from app.dependencies import User
from app.utils.logger import get_logger
from typing import Optional

logger = get_logger(__name__)


def _get_form_permissions(form_id: str) -> Optional[dict]:
    """
    Get permissions config for a form from the cached YAML mapping.

    Returns None if form not found or no permissions block (meaning admin-only).
    """
    from app.services.amis_jenkins_service import get_form_config

    form_config = get_form_config(form_id)
    if not form_config:
        return None
    return form_config.get("permissions")


def can_view_form(user: User, form_id: str) -> bool:
    """
    Check if user can view/access a form (form list, form page, schema, submit, history).

    Logic:
    1. admin -> True
    2. No permissions block -> False (admin-only)
    3. allowed_roles match -> True
    4. allowed_users match -> True
    5. False
    """
    if "admin" in user.roles:
        return True

    permissions = _get_form_permissions(form_id)
    if not permissions:
        return False

    # Check allowed_roles
    allowed_roles = permissions.get("allowed_roles", [])
    if any(role in user.roles for role in allowed_roles):
        return True

    # Check allowed_users
    allowed_users = permissions.get("allowed_users", [])
    if user.username in allowed_users:
        return True

    return False


def can_submit_form(user: User, form_id: str) -> bool:
    """
    Check if user can submit a form.
    Same logic as can_view_form (view + submit share the same gate).
    """
    return can_view_form(user, form_id)


def can_execute_pending_job(
    user: User, job_username: str, form_id: str
) -> bool:
    """
    Check if user can execute a pending job.

    Logic:
    1. admin -> True
    2. submitter (user.username == job_username) -> True
    3. No permissions block -> False
    4. execute_roles match -> True
    5. execute_users match -> True
    6. False
    """
    if "admin" in user.roles:
        return True

    # Submitter can always execute their own job
    if user.username == job_username:
        return True

    permissions = _get_form_permissions(form_id)
    if not permissions:
        return False

    # Check execute_roles
    execute_roles = permissions.get("execute_roles", [])
    if any(role in user.roles for role in execute_roles):
        return True

    # Check execute_users
    execute_users = permissions.get("execute_users", [])
    if user.username in execute_users:
        return True

    return False
