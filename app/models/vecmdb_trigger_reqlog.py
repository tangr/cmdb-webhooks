from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON
from typing import Optional, Dict, Any
import time


class VecmdbTriggerReqLogBase(SQLModel):
    target_name: str  # Target config name (e.g., "default1-add")
    request_id: str  # CMDB request UUID
    method: str  # Target API HTTP method
    path: str  # Target API path
    headers: Dict[str, Any] = Field(sa_column=Column(JSON))
    body: Dict[str, Any] = Field(sa_column=Column(JSON))
    clientip: str
    status: int
    target_response: Optional[Dict[str, Any]] = Field(
        sa_column=Column(JSON), default=None
    )
    error_message: Optional[str] = None


class VecmdbTriggerReqLog(VecmdbTriggerReqLogBase, table=True):
    __tablename__ = "vecmdb_trigger_reqlog"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: int = Field(default_factory=lambda: int(time.time()))
    updated_at: int = Field(default_factory=lambda: int(time.time()))


class VecmdbTriggerReqLogCreate(VecmdbTriggerReqLogBase):
    pass


class VecmdbTriggerReqLogUpdate(SQLModel):
    target_name: Optional[str] = None
    request_id: Optional[str] = None
    method: Optional[str] = None
    path: Optional[str] = None
    headers: Optional[Dict[str, Any]] = None
    body: Optional[Dict[str, Any]] = None
    clientip: Optional[str] = None
    status: Optional[int] = None
    target_response: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class VecmdbTriggerReqLogRead(VecmdbTriggerReqLogBase):
    """Model for API responses"""

    id: int
    created_at: int
    updated_at: int
