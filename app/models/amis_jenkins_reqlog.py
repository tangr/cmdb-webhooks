from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON
from typing import Optional, Dict, Any
import time


class AmisJenkinsReqLogBase(SQLModel):
    form_id: str  # Form ID
    form_title: str  # Form title
    trigger_type: str  # generic_webhook | remote_api
    jenkins_job: str  # Jenkins job name
    request_params: Dict[str, Any] = Field(sa_column=Column(JSON))  # User submitted params
    clientip: str
    username: str  # Submitting user
    status: int  # Response status code
    jenkins_response: Optional[Dict[str, Any]] = Field(
        sa_column=Column(JSON), default=None
    )
    error_message: Optional[str] = None


class AmisJenkinsReqLog(AmisJenkinsReqLogBase, table=True):
    __tablename__ = "amis_jenkins_reqlog"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: int = Field(default_factory=lambda: int(time.time()))
    updated_at: int = Field(default_factory=lambda: int(time.time()))


class AmisJenkinsReqLogCreate(AmisJenkinsReqLogBase):
    pass


class AmisJenkinsReqLogUpdate(SQLModel):
    form_id: Optional[str] = None
    form_title: Optional[str] = None
    trigger_type: Optional[str] = None
    jenkins_job: Optional[str] = None
    request_params: Optional[Dict[str, Any]] = None
    clientip: Optional[str] = None
    username: Optional[str] = None
    status: Optional[int] = None
    jenkins_response: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class AmisJenkinsReqLogRead(AmisJenkinsReqLogBase):
    """Model for API responses"""

    id: int
    created_at: int
    updated_at: int
