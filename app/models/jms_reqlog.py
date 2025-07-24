from sqlmodel import SQLModel, Field
from typing import Optional, Dict
import time


class JMSReqLogBase(SQLModel):
    host: str
    method: str
    path: str
    query: str
    headers: Dict
    body: Dict
    author: str
    status: int
    output: Optional[str] = None


class JMSReqLog(JMSReqLogBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: int = Field(default_factory=lambda: int(time.time()))
    updated_at: int = Field(default_factory=lambda: int(time.time()))


class JMSReqLogCreate(JMSReqLogBase):
    pass


class JMSReqLogUpdate(SQLModel):
    host: Optional[str] = None
    method: Optional[str] = None
    path: Optional[str] = None
    query: Optional[str] = None
    headers: Optional[Dict] = None
    body: Optional[Dict] = None
    author: Optional[str] = None
    status: Optional[int] = None
    output: Optional[str] = None
