from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON
from typing import Optional, Dict, Any
import time


class PendingJenkinsJobBase(SQLModel):
    """Base model for pending Jenkins job"""

    form_id: str = Field(description="Form ID from amis_jenkins_mapping")
    form_title: str = Field(description="Form display title")
    trigger_type: str = Field(description="Jenkins trigger type: generic_webhook or remote_api")
    jenkins_job: str = Field(description="Jenkins job path")
    request_params: Dict[str, Any] = Field(
        sa_column=Column(JSON), description="Original form parameters submitted by user"
    )
    username: str = Field(description="Submitting user from session")
    clientip: str = Field(description="Client IP address")
    approval_log_id: int = Field(description="Foreign key to feishu_approval_reqlog.id")
    status: str = Field(
        default="pending_approval",
        description="Job status: pending_approval, approved, expired, exhausted, rejected, canceled",
    )
    # Multi-execution support fields
    modifiable_fields_options: Optional[Dict[str, Any]] = Field(
        sa_column=Column(JSON),
        default=None,
        description="Snapshot of options for modifiable fields at submission time",
    )
    execution_count: int = Field(
        default=0, description="Number of times this job has been executed"
    )
    max_executions: int = Field(
        default=0, description="Maximum allowed executions (0 = unlimited)"
    )
    expire_at: int = Field(
        default=0, description="Expiration timestamp (0 = never expires)"
    )
    # Last execution response (for display purposes)
    jenkins_response: Optional[Dict[str, Any]] = Field(
        sa_column=Column(JSON), default=None, description="Jenkins response from last execution"
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message from last execution"
    )


class PendingJenkinsJob(PendingJenkinsJobBase, table=True):
    """Database model for pending Jenkins job"""

    __tablename__ = "pending_jenkins_jobs"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: int = Field(default_factory=lambda: int(time.time()))
    updated_at: int = Field(default_factory=lambda: int(time.time()))


class PendingJenkinsJobCreate(PendingJenkinsJobBase):
    """Model for creating pending Jenkins job"""

    pass


class PendingJenkinsJobUpdate(SQLModel):
    """Model for updating pending Jenkins job"""

    status: Optional[str] = None
    execution_count: Optional[int] = None
    jenkins_response: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class PendingJenkinsJobRead(PendingJenkinsJobBase):
    """Model for API responses"""

    id: int
    created_at: int
    updated_at: int
