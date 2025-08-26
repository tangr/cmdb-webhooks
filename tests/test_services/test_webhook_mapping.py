import pytest
import yaml
from unittest.mock import Mock, patch, mock_open
from pathlib import Path

from app.services.webhook_mapping import (
    _find_project_root,
    load_webhook_mapping,
    init_webhook_mapping,
    get_webhook_id_by_name,
    get_webhook_name_by_id,
    _webhook_mapping,
)


@pytest.mark.unit
class TestWebhookMapping:
    """Test webhook mapping service functionality"""

    def setup_method(self):
        """Clear webhook mapping before each test"""
        global _webhook_mapping
        _webhook_mapping.clear()

    def test_find_project_root_with_requirements(self):
        """Test finding project root with requirements.txt"""
        mock_path = Mock(spec=Path)
        mock_path.resolve.return_value = mock_path
        mock_path.parents = [
            Mock(spec=Path),  # Parent 1
            Mock(spec=Path),  # Parent 2 (project root)
            Mock(spec=Path),  # Parent 3
        ]

        # Mock the existence check - only parent 2 has requirements.txt
        mock_path.parents[0].__truediv__.return_value.exists.return_value = False
        mock_path.parents[1].__truediv__.return_value.exists.return_value = True

        with patch("app.services.webhook_mapping.Path") as mock_path_class:
            mock_path_class.__file__ = "/app/services/webhook_mapping.py"
            mock_path_class.return_value.resolve.return_value = mock_path

            result = _find_project_root()

            assert result == mock_path.parents[1]

    def test_find_project_root_fallback(self):
        """Test finding project root fallback when requirements.txt not found"""
        mock_path = Mock(spec=Path)
        mock_path.resolve.return_value = mock_path
        mock_path.parent.parent.parent = "/fallback/path"
        mock_path.parents = [Mock(spec=Path), Mock(spec=Path)]  # Parent 1  # Parent 2

        # Mock all parents don't have requirements.txt
        for parent in mock_path.parents:
            parent.__truediv__.return_value.exists.return_value = False

        with patch("app.services.webhook_mapping.Path") as mock_path_class:
            mock_path_class.__file__ = "/app/services/webhook_mapping.py"
            mock_path_class.return_value.resolve.return_value = mock_path

            result = _find_project_root()

            assert result == "/fallback/path"

    @patch("app.services.webhook_mapping._find_project_root")
    def test_load_webhook_mapping_success(self, mock_find_root):
        """Test successful webhook mapping loading"""
        # Mock file content
        yaml_content = {
            "webhooks": {
                "abc123def456": "alertmanager-webhook",
                "xyz789uvw012": "grafana-notifications",
                "test123test456": "monitoring-alerts",
            }
        }

        mock_project_root = Mock()
        mock_config_path = mock_project_root / "config" / "webhook_mapping.yaml"
        mock_find_root.return_value = mock_project_root

        with patch("builtins.open", mock_open(read_data=yaml.dump(yaml_content))):
            with patch("yaml.safe_load", return_value=yaml_content):
                result = load_webhook_mapping()

                expected = {
                    "abc123def456": "alertmanager-webhook",
                    "xyz789uvw012": "grafana-notifications",
                    "test123test456": "monitoring-alerts",
                }
                assert result == expected

    @patch("app.services.webhook_mapping._find_project_root")
    def test_load_webhook_mapping_file_not_found(self, mock_find_root):
        """Test webhook mapping loading when file not found"""
        mock_project_root = Mock()
        mock_find_root.return_value = mock_project_root

        with patch("builtins.open", side_effect=FileNotFoundError):
            with patch("app.services.webhook_mapping.logger") as mock_logger:
                result = load_webhook_mapping()

                assert result == {}
                mock_logger.warning.assert_called_once()
                assert "not found" in mock_logger.warning.call_args[0][0]

    @patch("app.services.webhook_mapping._find_project_root")
    def test_load_webhook_mapping_yaml_error(self, mock_find_root):
        """Test webhook mapping loading with YAML parsing error"""
        mock_project_root = Mock()
        mock_find_root.return_value = mock_project_root

        with patch("builtins.open", mock_open(read_data="invalid: yaml: content: [")):
            with patch("yaml.safe_load", side_effect=yaml.YAMLError("Invalid YAML")):
                with patch("app.services.webhook_mapping.logger") as mock_logger:
                    result = load_webhook_mapping()

                    assert result == {}
                    mock_logger.error.assert_called_once()
                    assert "Error parsing" in mock_logger.error.call_args[0][0]

    @patch("app.services.webhook_mapping._find_project_root")
    def test_load_webhook_mapping_no_webhooks_section(self, mock_find_root):
        """Test webhook mapping loading when webhooks section is missing"""
        yaml_content = {"other_config": {"key": "value"}}
        mock_project_root = Mock()
        mock_find_root.return_value = mock_project_root

        with patch("builtins.open", mock_open(read_data=yaml.dump(yaml_content))):
            with patch("yaml.safe_load", return_value=yaml_content):
                result = load_webhook_mapping()

                assert result == {}

    @patch("app.services.webhook_mapping.load_webhook_mapping")
    def test_init_webhook_mapping(self, mock_load):
        """Test webhook mapping initialization"""
        mock_mapping = {"test123": "test-webhook", "prod456": "prod-alerts"}
        mock_load.return_value = mock_mapping

        with patch("app.services.webhook_mapping.logger") as mock_logger:
            init_webhook_mapping()

            global _webhook_mapping
            assert _webhook_mapping == mock_mapping
            mock_logger.info.assert_called_once()
            assert "Loaded 2 webhook mappings" in mock_logger.info.call_args[0][0]

    def test_get_webhook_id_by_name_found(self):
        """Test getting webhook ID by name when mapping exists"""
        global _webhook_mapping
        _webhook_mapping = {
            "abc123": "alertmanager",
            "def456": "grafana",
            "ghi789": "prometheus",
        }

        result = get_webhook_id_by_name("grafana")
        assert result == "def456"

    def test_get_webhook_id_by_name_not_found(self):
        """Test getting webhook ID by name when mapping doesn't exist"""
        global _webhook_mapping
        _webhook_mapping = {"abc123": "alertmanager", "def456": "grafana"}

        result = get_webhook_id_by_name("nonexistent")
        assert result is None

    def test_get_webhook_id_by_name_empty_mapping(self):
        """Test getting webhook ID by name when mapping is empty"""
        global _webhook_mapping
        _webhook_mapping = {}

        result = get_webhook_id_by_name("any-name")
        assert result is None

    def test_get_webhook_name_by_id_found(self):
        """Test getting webhook name by ID when mapping exists"""
        global _webhook_mapping
        _webhook_mapping = {
            "abc123": "alertmanager",
            "def456": "grafana",
            "ghi789": "prometheus",
        }

        result = get_webhook_name_by_id("def456")
        assert result == "grafana"

    def test_get_webhook_name_by_id_not_found(self):
        """Test getting webhook name by ID when mapping doesn't exist"""
        global _webhook_mapping
        _webhook_mapping = {"abc123": "alertmanager", "def456": "grafana"}

        result = get_webhook_name_by_id("nonexistent")
        assert result is None

    def test_get_webhook_name_by_id_empty_mapping(self):
        """Test getting webhook name by ID when mapping is empty"""
        global _webhook_mapping
        _webhook_mapping = {}

        result = get_webhook_name_by_id("any-id")
        assert result is None

    def test_bidirectional_mapping(self):
        """Test that webhook ID/name mapping works bidirectionally"""
        global _webhook_mapping
        _webhook_mapping = {
            "hook-001": "production-alerts",
            "hook-002": "staging-monitoring",
            "hook-003": "development-logs",
        }

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

    def test_duplicate_names_handling(self):
        """Test handling of duplicate webhook names (last one wins)"""
        global _webhook_mapping
        _webhook_mapping = {
            "hook-001": "alerts",
            "hook-002": "monitoring",
            "hook-003": "alerts",  # Duplicate name
        }

        # When looking up by name, should return the last one encountered
        result_id = get_webhook_id_by_name("alerts")
        # Could be either hook-001 or hook-003, depending on dict iteration order
        assert result_id in ["hook-001", "hook-003"]

        # Looking up by ID should still work correctly
        assert get_webhook_name_by_id("hook-001") == "alerts"
        assert get_webhook_name_by_id("hook-002") == "monitoring"
        assert get_webhook_name_by_id("hook-003") == "alerts"

    def test_case_sensitivity(self):
        """Test that webhook mapping is case sensitive"""
        global _webhook_mapping
        _webhook_mapping = {"hook-001": "AlertManager", "hook-002": "alertmanager"}

        assert get_webhook_id_by_name("AlertManager") == "hook-001"
        assert get_webhook_id_by_name("alertmanager") == "hook-002"
        assert get_webhook_id_by_name("ALERTMANAGER") is None

    def test_special_characters_in_names(self):
        """Test webhook mapping with special characters in names"""
        global _webhook_mapping
        _webhook_mapping = {
            "hook-001": "alert-manager_v2.0",
            "hook-002": "grafana@prod.example.com",
            "hook-003": "monitoring/alerts/critical",
        }

        assert get_webhook_id_by_name("alert-manager_v2.0") == "hook-001"
        assert get_webhook_id_by_name("grafana@prod.example.com") == "hook-002"
        assert get_webhook_id_by_name("monitoring/alerts/critical") == "hook-003"
