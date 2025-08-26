#!/usr/bin/env python3
"""
Simple test script to verify login configuration functionality
"""

import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.templating import Jinja2Templates
from fastapi import Request
from unittest.mock import Mock
from config.config import settings


def test_template_rendering():
    """Test template rendering with different configuration values"""

    templates = Jinja2Templates(directory="templates")

    # Import and register custom time filters
    from app.utils.template_filters import time_to_str, time_diff_now

    templates.env.filters["timeToStr"] = time_to_str
    templates.env.filters["timeDiffNow"] = time_diff_now

    # Mock request object
    request = Mock(spec=Request)
    request.url.path = "/auth/login-page"

    # Test Case 1: Both login methods enabled (default)
    print("=== Test Case 1: Both login methods enabled ===")
    context = {
        "request": request,
        "page_name": "Login",
        "oidc_login_button_text": settings.oidc_login_button_text,
        "enable_username_password_login": True,
        "enable_oidc_login": True,
    }

    response = templates.TemplateResponse(name="login.html", context=context)
    print("✓ Template rendered successfully with both methods enabled")

    # Test Case 2: Only username/password login enabled
    print("\n=== Test Case 2: Only username/password login enabled ===")
    context["enable_oidc_login"] = False

    response = templates.TemplateResponse(name="login.html", context=context)
    print("✓ Template rendered successfully with only username/password login")

    # Test Case 3: Only OIDC login enabled
    print("\n=== Test Case 3: Only OIDC login enabled ===")
    context["enable_username_password_login"] = False
    context["enable_oidc_login"] = True

    response = templates.TemplateResponse(name="login.html", context=context)
    print("✓ Template rendered successfully with only OIDC login")

    # Test Case 4: Both login methods disabled
    print("\n=== Test Case 4: Both login methods disabled ===")
    context["enable_username_password_login"] = False
    context["enable_oidc_login"] = False

    response = templates.TemplateResponse(name="login.html", context=context)
    print("✓ Template rendered successfully with both methods disabled")
    print("  (Should show warning message)")

    return True


def test_configuration_loading():
    """Test configuration values loading"""

    print("=== Configuration Loading Test ===")

    # Test default values
    print(f"enable_username_password_login: {settings.enable_username_password_login}")
    print(f"enable_oidc_login: {settings.enable_oidc_login}")
    print(f"oidc_login_button_text: {settings.oidc_login_button_text}")

    # Verify types
    assert isinstance(
        settings.enable_username_password_login, bool
    ), "enable_username_password_login should be boolean"
    assert isinstance(
        settings.enable_oidc_login, bool
    ), "enable_oidc_login should be boolean"

    print("✓ Configuration loading test passed")
    return True


if __name__ == "__main__":
    print("Testing Login Configuration Functionality\n")

    try:
        # Test configuration loading
        test_configuration_loading()
        print()

        # Test template rendering
        test_template_rendering()

        print("\n✅ All tests passed successfully!")
        print("\nNext steps:")
        print(
            "1. Test with environment variables: export enable_username_password_login=false"
        )
        print("2. Test with .env file configurations")
        print("3. Test actual web interface by starting the application")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
