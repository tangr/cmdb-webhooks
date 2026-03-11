from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON
from typing import Optional, Dict, Any
import time


class GitlabHookReqLogBase(SQLModel):
    event_type: str  # push, tag_push, merge_request
    project_path: str
    method: str
    path: str
    headers: Dict[str, Any] = Field(sa_column=Column(JSON))
    body: Dict[str, Any] = Field(sa_column=Column(JSON))
    clientip: str
    status: int
    jenkins_job: Optional[str] = None
    jenkins_response: Optional[Dict[str, Any]] = Field(
        sa_column=Column(JSON), default=None
    )
    error_message: Optional[str] = None


class GitlabHookReqLog(GitlabHookReqLogBase, table=True):
    __tablename__ = "gitlab_hook_reqlog"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: int = Field(default_factory=lambda: int(time.time()))
    updated_at: int = Field(default_factory=lambda: int(time.time()))


class GitlabHookReqLogCreate(GitlabHookReqLogBase):
    pass


class GitlabHookReqLogUpdate(SQLModel):
    event_type: Optional[str] = None
    project_path: Optional[str] = None
    method: Optional[str] = None
    path: Optional[str] = None
    headers: Optional[Dict[str, Any]] = None
    body: Optional[Dict[str, Any]] = None
    clientip: Optional[str] = None
    status: Optional[int] = None
    jenkins_job: Optional[str] = None
    jenkins_response: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class GitlabHookReqLogRead(GitlabHookReqLogBase):
    """Model for API responses"""

    id: int
    created_at: int
    updated_at: int
