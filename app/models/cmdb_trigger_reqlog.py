from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON
from typing import Optional, Dict, Any, List
import time


class CmdbTriggerReqLogBase(SQLModel):
    host: str
    method: str
    path: str
    query: str
    headers: Dict[str, Any] = Field(sa_column=Column(JSON))
    body: Dict[str, Any] = Field(sa_column=Column(JSON))
    author: str
    clientip: str
    status: int
    output: Optional[str] = None


class CmdbTriggerReqLog(CmdbTriggerReqLogBase, table=True):
    __tablename__ = "cmdb_trigger_reqlog"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: int = Field(default_factory=lambda: int(time.time()))
    updated_at: int = Field(default_factory=lambda: int(time.time()))


class CmdbTriggerReqLogCreate(CmdbTriggerReqLogBase):
    pass


class CmdbTriggerReqLogUpdate(SQLModel):
    host: Optional[str] = None
    method: Optional[str] = None
    path: Optional[str] = None
    query: Optional[str] = None
    headers: Optional[Dict[str, Any]] = None
    body: Optional[Dict[str, Any]] = None
    author: Optional[str] = None
    clientip: Optional[str] = None
    status: Optional[int] = None
    output: Optional[str] = None


class CmdbTriggerReqLogRead(CmdbTriggerReqLogBase):
    """Model for API responses"""

    id: int
    created_at: int
    updated_at: int


class PaginationUrls(SQLModel):
    """Model for pagination URLs"""

    current: str
    prev: Optional[str] = None
    next: Optional[str] = None


class PaginationInfo(SQLModel):
    """Model for pagination information"""

    per_page: int
    has_next: bool
    has_prev: bool
    urls: PaginationUrls


class CmdbTriggerReqLogListResponse(SQLModel):
    """Model for paginated log list response"""

    logs: List[CmdbTriggerReqLog]
    user: str
    limit: int
    pagination: PaginationInfo
