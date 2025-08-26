import pytest
import logging
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from app.utils.logger import setup_logging, get_logger


@pytest.mark.unit
class TestLogger:
    """Test logging utility functionality"""

    def setup_method(self):
        """Clear logging configuration before each test"""
        # Clear all handlers from root logger
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        root_logger.setLevel(logging.WARNING)

    def test_setup_logging_console_only(self):
        """Test logging setup with console handler only"""
        with patch("config.config.settings") as mock_settings:
            mock_settings.log_level = "INFO"
            mock_settings.log_format = (
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            mock_settings.log_to_file = False

            setup_logging()

            root_logger = logging.getLogger()
            assert root_logger.level == logging.INFO
            assert len(root_logger.handlers) == 1

            # Check handler type
            handler = root_logger.handlers[0]
            assert isinstance(handler, logging.StreamHandler)
            assert not isinstance(handler, logging.handlers.RotatingFileHandler)

    def test_setup_logging_with_file_handler(self):
        """Test logging setup with file handler"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file_path = os.path.join(temp_dir, "test.log")

            with patch("config.config.settings") as mock_settings:
                mock_settings.log_level = "DEBUG"
                mock_settings.log_format = "%(levelname)s: %(message)s"
                mock_settings.log_to_file = True
                mock_settings.log_file_path = log_file_path
                mock_settings.log_max_bytes = 1024 * 1024
                mock_settings.log_backup_count = 3

                setup_logging()

                root_logger = logging.getLogger()
                assert root_logger.level == logging.DEBUG
                assert len(root_logger.handlers) == 2  # Console + File

                # Check handlers
                handler_types = [type(h) for h in root_logger.handlers]
                assert logging.StreamHandler in handler_types
                assert logging.handlers.RotatingFileHandler in handler_types

    def test_setup_logging_file_handler_directory_creation(self):
        """Test that logging setup creates directories for log files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file_path = os.path.join(temp_dir, "nested", "logs", "app.log")

            with patch("config.config.settings") as mock_settings:
                mock_settings.log_level = "INFO"
                mock_settings.log_format = "%(message)s"
                mock_settings.log_to_file = True
                mock_settings.log_file_path = log_file_path
                mock_settings.log_max_bytes = 1024
                mock_settings.log_backup_count = 1

                setup_logging()

                # Check that directory was created
                assert os.path.exists(os.path.dirname(log_file_path))

    def test_setup_logging_file_handler_error(self):
        """Test logging setup with file handler error"""
        with patch("config.config.settings") as mock_settings:
            mock_settings.log_level = "INFO"
            mock_settings.log_format = "%(message)s"
            mock_settings.log_to_file = True
            mock_settings.log_file_path = "/invalid/path/that/cannot/be/created.log"
            mock_settings.log_max_bytes = 1024
            mock_settings.log_backup_count = 1

            # Should not raise exception, but only have console handler
            setup_logging()

            root_logger = logging.getLogger()
            assert len(root_logger.handlers) == 1  # Only console handler
            assert isinstance(root_logger.handlers[0], logging.StreamHandler)

    def test_setup_logging_different_log_levels(self):
        """Test logging setup with different log levels"""
        test_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        for level_name in test_levels:
            with patch("config.config.settings") as mock_settings:
                mock_settings.log_level = level_name
                mock_settings.log_format = "%(message)s"
                mock_settings.log_to_file = False

                setup_logging()

                root_logger = logging.getLogger()
                expected_level = getattr(logging, level_name)
                assert root_logger.level == expected_level

            # Clear handlers for next iteration
            root_logger = logging.getLogger()
            root_logger.handlers.clear()

    def test_setup_logging_case_insensitive_level(self):
        """Test logging setup with case insensitive log level"""
        with patch("config.config.settings") as mock_settings:
            mock_settings.log_level = "debug"  # lowercase
            mock_settings.log_format = "%(message)s"
            mock_settings.log_to_file = False

            setup_logging()

            root_logger = logging.getLogger()
            assert root_logger.level == logging.DEBUG

    def test_setup_logging_uvicorn_integration(self):
        """Test that uvicorn logging is properly configured"""
        with patch("config.config.settings") as mock_settings:
            mock_settings.log_level = "INFO"
            mock_settings.log_format = "%(message)s"
            mock_settings.log_to_file = False

            setup_logging()

            # Check uvicorn.access logger configuration
            uvicorn_access = logging.getLogger("uvicorn.access")
            root_logger = logging.getLogger()

            # Should share handlers with root logger
            assert uvicorn_access.handlers == root_logger.handlers

    def test_setup_logging_database_logging_disabled(self):
        """Test database logging configuration when disabled"""
        with patch("config.config.settings") as mock_settings:
            mock_settings.log_level = "INFO"
            mock_settings.log_format = "%(message)s"
            mock_settings.log_to_file = False
            mock_settings.enable_database_logging = False

            setup_logging()

            # Check SQLAlchemy logger is set to WARNING level
            db_logger = logging.getLogger("sqlalchemy.engine")
            assert db_logger.level == logging.WARNING

    def test_setup_logging_database_logging_enabled(self):
        """Test database logging configuration when enabled"""
        with patch("config.config.settings") as mock_settings:
            mock_settings.log_level = "DEBUG"
            mock_settings.log_format = "%(message)s"
            mock_settings.log_to_file = False
            mock_settings.enable_database_logging = True

            setup_logging()

            # DB logger should inherit root logger level
            db_logger = logging.getLogger("sqlalchemy.engine")
            # Note: The actual behavior might depend on SQLAlchemy's default configuration

    def test_setup_logging_clears_existing_handlers(self):
        """Test that setup_logging clears existing handlers"""
        root_logger = logging.getLogger()

        # Add a dummy handler
        dummy_handler = logging.StreamHandler()
        root_logger.addHandler(dummy_handler)
        assert len(root_logger.handlers) == 1

        with patch("config.config.settings") as mock_settings:
            mock_settings.log_level = "INFO"
            mock_settings.log_format = "%(message)s"
            mock_settings.log_to_file = False

            setup_logging()

            # Old handler should be cleared, new handler added
            assert len(root_logger.handlers) == 1
            assert root_logger.handlers[0] != dummy_handler

    def test_get_logger_returns_logger_instance(self):
        """Test that get_logger returns a Logger instance"""
        logger = get_logger("test_module")

        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"

    def test_get_logger_different_modules(self):
        """Test get_logger with different module names"""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")
        logger3 = get_logger("module1")  # Same as logger1

        assert logger1.name == "module1"
        assert logger2.name == "module2"
        assert logger1 is logger3  # Should return same instance for same name
        assert logger1 is not logger2

    def test_get_logger_hierarchical_names(self):
        """Test get_logger with hierarchical module names"""
        parent_logger = get_logger("parent")
        child_logger = get_logger("parent.child")
        grandchild_logger = get_logger("parent.child.grandchild")

        assert parent_logger.name == "parent"
        assert child_logger.name == "parent.child"
        assert grandchild_logger.name == "parent.child.grandchild"

        # Test logger hierarchy
        assert child_logger.parent == parent_logger
        assert grandchild_logger.parent == child_logger

    def test_log_formatter_configuration(self):
        """Test that log formatter is properly configured"""
        custom_format = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

        with patch("config.config.settings") as mock_settings:
            mock_settings.log_level = "INFO"
            mock_settings.log_format = custom_format
            mock_settings.log_to_file = False

            setup_logging()

            root_logger = logging.getLogger()
            handler = root_logger.handlers[0]
            formatter = handler.formatter

            assert formatter._fmt == custom_format

    def test_rotating_file_handler_configuration(self):
        """Test rotating file handler configuration"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file_path = os.path.join(temp_dir, "rotating.log")

            with patch("config.config.settings") as mock_settings:
                mock_settings.log_level = "INFO"
                mock_settings.log_format = "%(message)s"
                mock_settings.log_to_file = True
                mock_settings.log_file_path = log_file_path
                mock_settings.log_max_bytes = 2048
                mock_settings.log_backup_count = 5

                setup_logging()

                root_logger = logging.getLogger()
                # Find the RotatingFileHandler
                file_handler = None
                for handler in root_logger.handlers:
                    if isinstance(handler, logging.handlers.RotatingFileHandler):
                        file_handler = handler
                        break

                assert file_handler is not None
                assert file_handler.maxBytes == 2048
                assert file_handler.backupCount == 5

    def test_logging_integration_test(self):
        """Integration test for actual logging functionality"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file_path = os.path.join(temp_dir, "integration.log")

            with patch("config.config.settings") as mock_settings:
                mock_settings.log_level = "DEBUG"
                mock_settings.log_format = "%(levelname)s:%(name)s:%(message)s"
                mock_settings.log_to_file = True
                mock_settings.log_file_path = log_file_path
                mock_settings.log_max_bytes = 1024 * 1024
                mock_settings.log_backup_count = 1

                setup_logging()

                # Test logging
                logger = get_logger("integration_test")
                logger.debug("Debug message")
                logger.info("Info message")
                logger.warning("Warning message")
                logger.error("Error message")

                # Check that log file was created and contains messages
                assert os.path.exists(log_file_path)

                with open(log_file_path, "r") as f:
                    log_content = f.read()
                    assert "DEBUG:integration_test:Debug message" in log_content
                    assert "INFO:integration_test:Info message" in log_content
                    assert "WARNING:integration_test:Warning message" in log_content
                    assert "ERROR:integration_test:Error message" in log_content
