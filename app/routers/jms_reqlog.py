from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlmodel import select
from app.models.jms_reqlog import JMSReqLog, JMSReqLogCreate, JMSReqLogUpdate
from app.dependencies import (
    SessionDep,
    get_current_user_flexible,
    get_current_user_any_required,
    require_roles,
    User,
)
from typing import List, Optional
import time
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")

router = APIRouter()


# ==================== Public Endpoints (No Authentication) ====================
@router.get("/", response_class=HTMLResponse)
def read_all_logs(
    session: SessionDep,
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_flexible),
):
    """获取所有日志记录 (Public endpoint for webhook receiving)"""
    statement = select(JMSReqLog)
    logs = session.exec(statement).all()
    return templates.TemplateResponse(
        request=request,
        name="show.html",
        context={
            "jobs": logs,
            "current_user": current_user,
            "page_name": "Logs",
            "url": request.url_for("read_all_logs"),
        },
    )


@router.post("/", response_model=JMSReqLog)
def create_log(log: JMSReqLogCreate, session: SessionDep):
    """创建新的日志记录 (Public endpoint for webhook receiving)"""
    db_log = JMSReqLog(**log.model_dump())
    session.add(db_log)
    session.commit()
    session.refresh(db_log)
    return db_log


# ==================== User-Level Endpoints (Flexible Authentication) ====================
@router.get("/list", response_model=List[JMSReqLog])
def read_logs_with_pagination(
    session: SessionDep,
    current_user: Optional[User] = Depends(get_current_user_flexible),
    skip: int = 0,
    limit: int = 100,
):
    """分页获取日志记录 (Supports both JWT and Session auth)"""
    # Optional authentication - provides more features if authenticated
    if current_user:
        # Authenticated users can see more details or have higher limits
        limit = min(limit, 1000)  # Higher limit for authenticated users
    else:
        # Anonymous users have restricted access
        limit = min(limit, 10)  # Lower limit for anonymous users

    statement = select(JMSReqLog).offset(skip).limit(limit)
    logs = session.exec(statement).all()

    return {
        "logs": logs,
        "user": current_user.username if current_user else "anonymous",
        "limit": limit,
    }


@router.get("/{log_id}", response_model=JMSReqLog)
def read_log_by_id(
    log_id: int,
    session: SessionDep,
    current_user: User = Depends(get_current_user_any_required),
):
    """根据ID获取单条日志记录 (Requires authentication via JWT or Session)"""
    log = session.get(JMSReqLog, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    return log


# ==================== Admin-Level Endpoints (Role-based Access Control) ====================
@router.put("/{log_id}", response_model=JMSReqLog)
def update_log(
    log_id: int,
    update: JMSReqLogUpdate,
    session: SessionDep,
    current_user: User = Depends(require_roles("admin")),
):
    """更新日志记录 (Requires admin role)"""
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
def delete_log(
    log_id: int,
    session: SessionDep,
    current_user: User = Depends(require_roles("admin")),
):
    """删除日志记录 (Requires admin role)"""
    log = session.get(JMSReqLog, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")

    session.delete(log)
    session.commit()
    return {"message": "Log deleted successfully", "deleted_by": current_user.username}
