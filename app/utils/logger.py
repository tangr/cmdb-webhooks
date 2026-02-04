import logging
import logging.handlers
import os
from config.config import settings


def setup_logging():
    """Configure application logging based on settings"""
    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))

    # Clear existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(settings.log_format)

    # Console handler (always enabled for now, can be controlled by setting)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (optional)
    if settings.log_to_file:
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(settings.log_file_path), exist_ok=True)

            file_handler = logging.handlers.RotatingFileHandler(
                settings.log_file_path,
                maxBytes=settings.log_max_bytes,
                backupCount=settings.log_backup_count,
            )
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            logging.error(f"Failed to setup file logging: {e}")

    # Configure FastAPI access logs
    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.handlers = root_logger.handlers

    # Configure database logging
    if not settings.enable_database_logging:
        db_logger = logging.getLogger("sqlalchemy.engine")
        db_logger.setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module"""
    return logging.getLogger(name)
