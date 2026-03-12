"""
Feishu Approval service for handling approval business logic.

This service handles:
- Creating approval instances via Feishu API
- Querying approval status
- Logging all requests to database
"""

import logging
import time
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from app.models.feishu_approval_reqlog import (
    FeishuApprovalReqLog,
    FeishuApprovalReqLogCreate,
    FeishuApprovalReqLogRead,
)
from app.services.feishu_client import FeishuClient, FeishuClientConfig
from config.config import settings

logger = logging.getLogger(__name__)


def log_approval_request(session: Session, log_entry: FeishuApprovalReqLogCreate):
    """
    Log approval request to database and/or console based on configuration.

    Args:
        session: Database session
        log_entry: Log entry to save
    """
    # Console logging
    if settings.enable_console_logging:
        log_message = (
            f"Feishu Approval - "
            f"App: {log_entry.app_name}, "
            f"User: {log_entry.username}, "
            f"FeishuUser: {log_entry.feishu_user_id}, "
            f"Status: {log_entry.status}, "
            f"Client IP: {log_entry.clientip}"
        )

        if log_entry.error_message:
            log_message += f", Error: {log_entry.error_message}"
            logger.error(log_message)
        else:
            logger.info(log_message)

    # Database logging
    if settings.enable_database_logging:
        try:
            db_log = FeishuApprovalReqLog(**log_entry.model_dump())
            session.add(db_log)
            session.commit()
            session.refresh(db_log)
            return db_log
        except Exception as e:
            if settings.enable_console_logging:
                logger.error(f"Failed to save approval log to database: {str(e)}")
            raise

    return None


class FeishuApprovalService:
    """Service for handling Feishu approval operations"""

    @staticmethod
    def get_available_apps() -> List[Dict[str, str]]:
        """
        Get list of available Feishu apps from configuration.

        Returns:
            List of app info dicts with name and description
        """
        config = FeishuClientConfig.load_config()
        apps = config.get("apps", {})
        return [
            {"name": name, "description": app_config.get("description", "")}
            for name, app_config in apps.items()
        ]

    @staticmethod
    async def create_approval(
        session: Session,
        app_name: str,
        feishu_user_id: str,
        form_data: Dict[str, Any],
        username: str,
        clientip: str,
        approval_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new approval instance.

        Args:
            session: Database session
            app_name: Feishu app name from config
            feishu_user_id: Feishu user ID (short format)
            form_data: Form data to submit
            username: Username from session (who triggered this)
            clientip: Client IP address
            approval_code: Optional approval code (uses default from config if not provided)

        Returns:
            Dict with approval creation result
        """
        # Get app config to get approval_code
        app_config = FeishuClientConfig.get_app_config(app_name)
        if not app_config:
            raise ValueError(f"App config not found for: {app_name}")

        code = approval_code or app_config.get("approval_code")
        if not code:
            raise ValueError(f"No approval_code configured for app: {app_name}")

        # Prepare log entry
        log_entry = FeishuApprovalReqLogCreate(
            app_name=app_name,
            approval_code=code,
            feishu_user_id=feishu_user_id,
            status="pending",
            form_data=form_data,
            username=username,
            clientip=clientip,
        )

        try:
            # Create Feishu client and call API
            client = FeishuClient(app_name)
            result = await client.create_approval_instance(
                user_id=feishu_user_id,
                form_data=form_data,
                approval_code=code,
            )

            # Update log entry with success
            log_entry.feishu_instance_code = result["instance_code"]
            log_entry.feishu_response = result.get("raw_response")

            # Save log to database
            db_log = log_approval_request(session, log_entry)

            return {
                "success": True,
                "log_id": db_log.id if db_log else None,
                "feishu_instance_code": result["instance_code"],
                "status": "pending",
            }

        except Exception as e:
            # Update log entry with error
            log_entry.status = "error"
            log_entry.error_message = str(e)

            # Save error log to database
            db_log = log_approval_request(session, log_entry)

            logger.error(f"Failed to create approval: {e}")
            raise

    @staticmethod
    async def get_approval_status(
        session: Session, log_id: int
    ) -> Dict[str, Any]:
        """
        Get approval status by log ID.

        This queries the Feishu API to get the latest status and updates the database.

        Args:
            session: Database session
            log_id: Database log ID

        Returns:
            Dict with approval status
        """
        # Get log from database
        log = session.get(FeishuApprovalReqLog, log_id)
        if not log:
            raise ValueError(f"Approval log not found: {log_id}")

        if not log.feishu_instance_code:
            return {
                "log_id": log_id,
                "status": log.status,
                "error": "No Feishu instance code - approval creation may have failed",
            }

        try:
            # Query Feishu API for latest status
            client = FeishuClient(log.app_name)
            result = await client.get_approval_instance(log.feishu_instance_code)

            # Update status in database if changed
            new_status = result.get("status", log.status)
            if new_status != log.status:
                log.status = new_status
                log.updated_at = int(time.time())
                log.feishu_response = result.get("raw_response")
                session.add(log)
                session.commit()

            return {
                "log_id": log_id,
                "feishu_instance_code": log.feishu_instance_code,
                "status": new_status,
                "feishu_status": result.get("feishu_status"),
                "created_at": log.created_at,
                "updated_at": log.updated_at,
            }

        except Exception as e:
            logger.error(f"Failed to get approval status: {e}")
            return {
                "log_id": log_id,
                "feishu_instance_code": log.feishu_instance_code,
                "status": log.status,
                "error": f"Failed to sync status from Feishu: {str(e)}",
                "created_at": log.created_at,
                "updated_at": log.updated_at,
            }

    @staticmethod
    async def get_approval_status_by_instance_code(
        session: Session, instance_code: str, app_name: str = "default"
    ) -> Dict[str, Any]:
        """
        Get approval status by Feishu instance code.

        Args:
            session: Database session
            instance_code: Feishu approval instance code
            app_name: Feishu app name (needed to get credentials)

        Returns:
            Dict with approval status
        """
        try:
            # Query Feishu API directly
            client = FeishuClient(app_name)
            result = await client.get_approval_instance(instance_code)

            # Try to find and update local record
            statement = select(FeishuApprovalReqLog).where(
                FeishuApprovalReqLog.feishu_instance_code == instance_code
            )
            log = session.exec(statement).first()

            if log:
                new_status = result.get("status", log.status)
                if new_status != log.status:
                    log.status = new_status
                    log.updated_at = int(time.time())
                    log.feishu_response = result.get("raw_response")
                    session.add(log)
                    session.commit()

                return {
                    "log_id": log.id,
                    "feishu_instance_code": instance_code,
                    "status": new_status,
                    "feishu_status": result.get("feishu_status"),
                    "created_at": log.created_at,
                    "updated_at": log.updated_at,
                }

            # No local record, return Feishu data only
            return {
                "feishu_instance_code": instance_code,
                "status": result.get("status"),
                "feishu_status": result.get("feishu_status"),
            }

        except Exception as e:
            logger.error(f"Failed to get approval status: {e}")
            raise

    @staticmethod
    def list_approvals(
        session: Session,
        username: Optional[str] = None,
        app_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        List approval records with optional filters.

        Args:
            session: Database session
            username: Filter by username
            app_name: Filter by app name
            status: Filter by status
            limit: Max records to return
            offset: Offset for pagination

        Returns:
            Dict with records and pagination info
        """
        statement = select(FeishuApprovalReqLog)

        if username:
            statement = statement.where(FeishuApprovalReqLog.username == username)
        if app_name:
            statement = statement.where(FeishuApprovalReqLog.app_name == app_name)
        if status:
            statement = statement.where(FeishuApprovalReqLog.status == status)

        # Order by created_at desc
        statement = statement.order_by(FeishuApprovalReqLog.created_at.desc())
        statement = statement.offset(offset).limit(limit)

        records = session.exec(statement).all()

        return {
            "total": len(records),
            "limit": limit,
            "offset": offset,
            "records": [
                FeishuApprovalReqLogRead.model_validate(r).model_dump()
                for r in records
            ],
        }

    @staticmethod
    def get_approval_by_id(session: Session, log_id: int) -> Optional[FeishuApprovalReqLogRead]:
        """
        Get a single approval record by ID.

        Args:
            session: Database session
            log_id: Database log ID

        Returns:
            Approval record or None
        """
        log = session.get(FeishuApprovalReqLog, log_id)
        if log:
            return FeishuApprovalReqLogRead.model_validate(log)
        return None
