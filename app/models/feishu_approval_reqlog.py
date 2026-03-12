from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON
from typing import Optional, Dict, Any
import time


class FeishuApprovalReqLogBase(SQLModel):
    """Base model for Feishu Approval request log"""

    app_name: str = Field(description="Feishu app name from config")
    approval_code: str = Field(description="Feishu approval definition code")
    feishu_instance_code: Optional[str] = Field(
        default=None, description="Feishu approval instance code returned by API"
    )
    feishu_user_id: str = Field(description="Feishu user ID (short format)")
    status: str = Field(
        default="pending", description="Approval status: pending, approved, rejected, canceled"
    )
    form_data: Dict[str, Any] = Field(
        sa_column=Column(JSON), description="Form data submitted with approval"
    )
    username: str = Field(description="Submitting user from session")
    clientip: str = Field(description="Client IP address")
    feishu_response: Optional[Dict[str, Any]] = Field(
        sa_column=Column(JSON), default=None, description="Response from Feishu API"
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message if request failed"
    )


class FeishuApprovalReqLog(FeishuApprovalReqLogBase, table=True):
    """Database model for Feishu Approval request log"""

    __tablename__ = "feishu_approval_reqlog"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: int = Field(default_factory=lambda: int(time.time()))
    updated_at: int = Field(default_factory=lambda: int(time.time()))


class FeishuApprovalReqLogCreate(FeishuApprovalReqLogBase):
    """Model for creating Feishu Approval request log"""

    pass


class FeishuApprovalReqLogUpdate(SQLModel):
    """Model for updating Feishu Approval request log"""

    feishu_instance_code: Optional[str] = None
    status: Optional[str] = None
    feishu_response: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class FeishuApprovalReqLogRead(FeishuApprovalReqLogBase):
    """Model for API responses"""

    id: int
    created_at: int
    updated_at: int
