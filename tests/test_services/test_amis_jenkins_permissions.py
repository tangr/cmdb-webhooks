import pytest
from unittest.mock import patch, MagicMock
from app.dependencies import User
from app.services.amis_jenkins_permissions import (
    can_view_form,
    can_submit_form,
    can_execute_pending_job,
    _get_form_permissions,
)


# Mock form configs for testing
MOCK_FORMS = {
    "form-with-roles": {
        "title": "Form with roles",
        "jenkins_job": "test/job1",
        "permissions": {
            "allowed_roles": ["deploy-prod", "deploy-staging"],
            "allowed_users": ["special-user"],
            "execute_roles": ["deploy-prod"],
            "execute_users": ["ops-user"],
        },
    },
    "form-roles-only": {
        "title": "Form roles only",
        "jenkins_job": "test/job2",
        "permissions": {
            "allowed_roles": ["deploy-prod"],
        },
    },
    "form-users-only": {
        "title": "Form users only",
        "jenkins_job": "test/job3",
        "permissions": {
            "allowed_users": ["alice", "bob"],
        },
    },
    "form-no-permissions": {
        "title": "Admin only form",
        "jenkins_job": "test/job4",
        # No permissions block = admin-only
    },
    "form-empty-permissions": {
        "title": "Empty permissions form",
        "jenkins_job": "test/job5",
        "permissions": {},
    },
}


def _mock_get_form_config(form_id):
    """Mock get_form_config to return test form configs."""
    return MOCK_FORMS.get(form_id)


@pytest.fixture(autouse=True)
def mock_form_config():
    """Patch get_form_config for all tests in this module."""
    with patch(
        "app.services.amis_jenkins_service.get_form_config",
        side_effect=_mock_get_form_config,
    ):
        yield


# ==================== Test Users ====================
def make_user(username, roles):
    return User(user_id=f"id-{username}", username=username, roles=roles)


admin_user = make_user("admin", ["admin", "user"])
deploy_prod_user = make_user("deployer", ["user", "deploy-prod"])
deploy_staging_user = make_user("stager", ["user", "deploy-staging"])
regular_user = make_user("regular", ["user"])
special_user = make_user("special-user", ["user"])
alice_user = make_user("alice", ["user"])
ops_user = make_user("ops-user", ["user"])
no_role_user = make_user("norole", [])


# ==================== can_view_form tests ====================
@pytest.mark.unit
class TestCanViewForm:
    """Test can_view_form permission checking."""

    def test_admin_can_view_any_form(self):
        """Admin role bypasses all form view checks."""
        assert can_view_form(admin_user, "form-with-roles") is True
        assert can_view_form(admin_user, "form-no-permissions") is True
        assert can_view_form(admin_user, "form-empty-permissions") is True

    def test_allowed_roles_grants_access(self):
        """User with matching role in allowed_roles can view form."""
        assert can_view_form(deploy_prod_user, "form-with-roles") is True
        assert can_view_form(deploy_staging_user, "form-with-roles") is True

    def test_allowed_users_grants_access(self):
        """User explicitly listed in allowed_users can view form."""
        assert can_view_form(special_user, "form-with-roles") is True

    def test_no_permissions_block_admin_only(self):
        """Form without permissions block is accessible only to admin."""
        assert can_view_form(regular_user, "form-no-permissions") is False
        assert can_view_form(deploy_prod_user, "form-no-permissions") is False

    def test_empty_permissions_denies_non_admin(self):
        """Form with empty permissions block denies non-admin users."""
        assert can_view_form(regular_user, "form-empty-permissions") is False

    def test_unauthorized_user_denied(self):
        """User without matching role or username is denied."""
        assert can_view_form(regular_user, "form-with-roles") is False

    def test_nonexistent_form_denied(self):
        """Nonexistent form ID returns False."""
        assert can_view_form(admin_user, "nonexistent-form") is True  # admin bypasses
        assert can_view_form(regular_user, "nonexistent-form") is False

    def test_roles_only_form(self):
        """Form with only allowed_roles configured."""
        assert can_view_form(deploy_prod_user, "form-roles-only") is True
        assert can_view_form(deploy_staging_user, "form-roles-only") is False

    def test_users_only_form(self):
        """Form with only allowed_users configured."""
        assert can_view_form(alice_user, "form-users-only") is True
        assert can_view_form(regular_user, "form-users-only") is False

    def test_user_with_no_roles(self):
        """User with empty roles list is denied."""
        assert can_view_form(no_role_user, "form-with-roles") is False


# ==================== can_submit_form tests ====================
@pytest.mark.unit
class TestCanSubmitForm:
    """Test can_submit_form (same logic as can_view_form)."""

    def test_submit_same_as_view(self):
        """can_submit_form has identical behavior to can_view_form."""
        assert can_submit_form(admin_user, "form-with-roles") is True
        assert can_submit_form(deploy_prod_user, "form-with-roles") is True
        assert can_submit_form(regular_user, "form-with-roles") is False
        assert can_submit_form(regular_user, "form-no-permissions") is False


# ==================== can_execute_pending_job tests ====================
@pytest.mark.unit
class TestCanExecutePendingJob:
    """Test can_execute_pending_job permission checking."""

    def test_admin_can_execute_any_job(self):
        """Admin role can execute any pending job."""
        assert (
            can_execute_pending_job(admin_user, "other-user", "form-with-roles") is True
        )
        assert (
            can_execute_pending_job(admin_user, "other-user", "form-no-permissions")
            is True
        )

    def test_submitter_can_execute_own_job(self):
        """Job submitter can always execute their own pending job."""
        assert (
            can_execute_pending_job(regular_user, "regular", "form-with-roles") is True
        )
        assert (
            can_execute_pending_job(regular_user, "regular", "form-no-permissions")
            is True
        )

    def test_execute_roles_grants_execution(self):
        """User with matching execute_role can execute others' jobs."""
        # deploy-prod is in execute_roles for form-with-roles
        assert (
            can_execute_pending_job(deploy_prod_user, "other-user", "form-with-roles")
            is True
        )

    def test_execute_users_grants_execution(self):
        """User listed in execute_users can execute others' jobs."""
        # ops-user is in execute_users for form-with-roles
        assert (
            can_execute_pending_job(ops_user, "other-user", "form-with-roles") is True
        )

    def test_non_submitter_without_execute_permission_denied(self):
        """Non-submitter without execute_roles/execute_users is denied."""
        assert (
            can_execute_pending_job(regular_user, "other-user", "form-with-roles")
            is False
        )

    def test_allowed_role_without_execute_role_denied(self):
        """User with allowed_role but not execute_role cannot execute others' jobs."""
        # deploy-staging is in allowed_roles but not in execute_roles
        assert (
            can_execute_pending_job(
                deploy_staging_user, "other-user", "form-with-roles"
            )
            is False
        )

    def test_no_permissions_non_submitter_denied(self):
        """Non-admin, non-submitter on form without permissions is denied."""
        assert (
            can_execute_pending_job(
                deploy_prod_user, "other-user", "form-no-permissions"
            )
            is False
        )

    def test_form_without_execute_config(self):
        """Form with permissions but no execute_roles/execute_users."""
        # form-roles-only has no execute_roles/execute_users
        assert (
            can_execute_pending_job(
                deploy_prod_user, "other-user", "form-roles-only"
            )
            is False
        )
        # But submitter still can
        assert (
            can_execute_pending_job(
                deploy_prod_user, "deployer", "form-roles-only"
            )
            is True
        )


# ==================== _get_form_permissions tests ====================
@pytest.mark.unit
class TestGetFormPermissions:
    """Test _get_form_permissions helper."""

    def test_returns_permissions_dict(self):
        """Returns permissions dict when configured."""
        perms = _get_form_permissions("form-with-roles")
        assert perms is not None
        assert "allowed_roles" in perms

    def test_returns_none_for_no_permissions(self):
        """Returns None when no permissions block."""
        perms = _get_form_permissions("form-no-permissions")
        assert perms is None

    def test_returns_none_for_nonexistent_form(self):
        """Returns None for nonexistent form."""
        perms = _get_form_permissions("nonexistent-form")
        assert perms is None

    def test_returns_empty_dict_for_empty_permissions(self):
        """Returns empty dict for form with empty permissions block."""
        perms = _get_form_permissions("form-empty-permissions")
        assert perms == {}
