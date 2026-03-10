from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON
from typing import Optional, Dict, Any
import time


class FeishuBotReqLogBase(SQLModel):
    webhook_id: str
    method: str
    path: str
    query: str
    headers: Dict[str, Any] = Field(sa_column=Column(JSON))
    body: Dict[str, Any] = Field(sa_column=Column(JSON))
    clientip: str
    status: int
    response_headers: Optional[Dict[str, Any]] = Field(
        sa_column=Column(JSON), default=None
    )
    response_body: Optional[Dict[str, Any]] = Field(
        sa_column=Column(JSON), default=None
    )
    error_message: Optional[str] = None


class FeishuBotReqLog(FeishuBotReqLogBase, table=True):
    __tablename__ = "feishu_bot_reqlog"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: int = Field(default_factory=lambda: int(time.time()))
    updated_at: int = Field(default_factory=lambda: int(time.time()))


class FeishuBotReqLogCreate(FeishuBotReqLogBase):
    pass


class FeishuBotReqLogUpdate(SQLModel):
    webhook_id: Optional[str] = None
    method: Optional[str] = None
    path: Optional[str] = None
    query: Optional[str] = None
    headers: Optional[Dict[str, Any]] = None
    body: Optional[Dict[str, Any]] = None
    clientip: Optional[str] = None
    status: Optional[int] = None
    response_headers: Optional[Dict[str, Any]] = None
    response_body: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class FeishuBotReqLogRead(FeishuBotReqLogBase):
    """Model for API responses"""

    id: int
    created_at: int
    updated_at: int
