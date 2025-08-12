from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import select
from app.models.jms_reqlog import JMSReqLog, JMSReqLogCreate, JMSReqLogUpdate
from app.dependencies import SessionDep
from typing import List
import time
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")

router = APIRouter()


@router.get("/", response_model=List[JMSReqLog])
def read_all_logs(session: SessionDep, request: Request):
    """获取所有日志记录"""
    statement = select(JMSReqLog)
    logs = session.exec(statement).all()
    return templates.TemplateResponse(
        request=request, name="show.html", context={"jobs": logs}
    )
    return logs


@router.get("/list", response_model=List[JMSReqLog])
def read_logs_with_pagination(session: SessionDep, skip: int = 0, limit: int = 100):
    """分页获取日志记录"""
    statement = select(JMSReqLog).offset(skip).limit(limit)
    logs = session.exec(statement).all()
    return logs


@router.post("/", response_model=JMSReqLog)
def create_log(log: JMSReqLogCreate, session: SessionDep):
    """创建新的日志记录"""
    db_log = JMSReqLog(**log.model_dump())
    session.add(db_log)
    session.commit()
    session.refresh(db_log)
    return db_log


@router.get("/{log_id}", response_model=JMSReqLog)
def read_log_by_id(log_id: int, session: SessionDep):
    """根据ID获取单条日志记录"""
    log = session.get(JMSReqLog, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    return log


@router.put("/{log_id}", response_model=JMSReqLog)
def update_log(log_id: int, update: JMSReqLogUpdate, session: SessionDep):
    """更新日志记录"""
    log = session.get(JMSReqLog, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")

    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(log, key, value)

    log.updated_at = int(time.time())
    session.add(log)
    session.commit()
    session.refresh(log)
    return log


@router.delete("/{log_id}")
def delete_log(log_id: int, session: SessionDep):
    """删除日志记录"""
    log = session.get(JMSReqLog, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")

    session.delete(log)
    session.commit()
    return {"message": "Log deleted successfully"}
