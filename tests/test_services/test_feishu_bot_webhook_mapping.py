import pytest
from unittest.mock import patch

from app.services.feishu_bot_service import (
    get_webhook_id_by_name,
    get_webhook_name_by_id,
)


@pytest.mark.unit
class TestWebhookMapping:
    """Test webhook mapping functions in feishu_bot_service"""

    def test_get_webhook_id_by_name_found(self):
        """Test getting webhook ID by name when mapping exists"""
        mock_config = {
            "feishu_bot_webhook_mappings": {
                "abc123": "alertmanager",
                "def456": "grafana",
                "ghi789": "prometheus",
            }
        }

        with patch("app.services.feishu_bot_service._feishu_bot_config", mock_config):
            result = get_webhook_id_by_name("grafana")
            assert result == "def456"

    def test_get_webhook_id_by_name_not_found(self):
        """Test getting webhook ID by name when mapping doesn't exist"""
        mock_config = {
            "feishu_bot_webhook_mappings": {
                "abc123": "alertmanager",
                "def456": "grafana",
            }
        }

        with patch("app.services.feishu_bot_service._feishu_bot_config", mock_config):
            result = get_webhook_id_by_name("nonexistent")
            assert result is None

    def test_get_webhook_id_by_name_empty_mapping(self):
        """Test getting webhook ID by name when mapping is empty"""
        mock_config = {"feishu_bot_webhook_mappings": {}}

        with patch("app.services.feishu_bot_service._feishu_bot_config", mock_config):
            result = get_webhook_id_by_name("any-name")
            assert result is None

    def test_get_webhook_id_by_name_no_mapping_key(self):
        """Test getting webhook ID by name when mapping key is missing"""
        mock_config = {}

        with patch("app.services.feishu_bot_service._feishu_bot_config", mock_config):
            result = get_webhook_id_by_name("any-name")
            assert result is None

    def test_get_webhook_name_by_id_found(self):
        """Test getting webhook name by ID when mapping exists"""
        mock_config = {
            "feishu_bot_webhook_mappings": {
                "abc123": "alertmanager",
                "def456": "grafana",
                "ghi789": "prometheus",
            }
        }

        with patch("app.services.feishu_bot_service._feishu_bot_config", mock_config):
            result = get_webhook_name_by_id("def456")
            assert result == "grafana"

    def test_get_webhook_name_by_id_not_found(self):
        """Test getting webhook name by ID when mapping doesn't exist"""
        mock_config = {
            "feishu_bot_webhook_mappings": {
                "abc123": "alertmanager",
                "def456": "grafana",
            }
        }

        with patch("app.services.feishu_bot_service._feishu_bot_config", mock_config):
            result = get_webhook_name_by_id("nonexistent")
            assert result is None

    def test_get_webhook_name_by_id_empty_mapping(self):
        """Test getting webhook name by ID when mapping is empty"""
        mock_config = {"feishu_bot_webhook_mappings": {}}

        with patch("app.services.feishu_bot_service._feishu_bot_config", mock_config):
            result = get_webhook_name_by_id("any-id")
            assert result is None

    def test_bidirectional_mapping(self):
        """Test that webhook ID/name mapping works bidirectionally"""
        mock_config = {
            "feishu_bot_webhook_mappings": {
                "hook-001": "production-alerts",
                "hook-002": "staging-monitoring",
                "hook-003": "development-logs",
            }
        }

        with patch("app.services.feishu_bot_service._feishu_bot_config", mock_config):
            # Test ID to name
            assert get_webhook_name_by_id("hook-002") == "staging-monitoring"

            # Test name to ID
            assert get_webhook_id_by_name("staging-monitoring") == "hook-002"

            # Test round trip
            webhook_id = "hook-001"
            webhook_name = get_webhook_name_by_id(webhook_id)
            assert webhook_name == "production-alerts"

            found_id = get_webhook_id_by_name(webhook_name)
            assert found_id == webhook_id

    def test_case_sensitivity(self):
        """Test that webhook mapping is case sensitive"""
        mock_config = {
            "feishu_bot_webhook_mappings": {
                "hook-001": "AlertManager",
                "hook-002": "alertmanager",
            }
        }

        with patch("app.services.feishu_bot_service._feishu_bot_config", mock_config):
            assert get_webhook_id_by_name("AlertManager") == "hook-001"
            assert get_webhook_id_by_name("alertmanager") == "hook-002"
            assert get_webhook_id_by_name("ALERTMANAGER") is None

    def test_special_characters_in_names(self):
        """Test webhook mapping with special characters in names"""
        mock_config = {
            "feishu_bot_webhook_mappings": {
                "hook-001": "alert-manager_v2.0",
                "hook-002": "grafana@prod.example.com",
                "hook-003": "monitoring/alerts/critical",
            }
        }

        with patch("app.services.feishu_bot_service._feishu_bot_config", mock_config):
            assert get_webhook_id_by_name("alert-manager_v2.0") == "hook-001"
            assert get_webhook_id_by_name("grafana@prod.example.com") == "hook-002"
            assert get_webhook_id_by_name("monitoring/alerts/critical") == "hook-003"
