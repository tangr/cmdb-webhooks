from fastapi import APIRouter, Depends, HTTPException, Request, Header
from fastapi.responses import HTMLResponse
from sqlmodel import select, func, desc
from app.models.jms_reqlog import (
    JMSReqLog,
    JMSReqLogCreate,
    JMSReqLogUpdate,
    JMSReqLogListResponse,
)
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
from app.utils.template_filters import time_to_str, time_diff_now
from app.utils.webhook_security import verify_jms_webhook, verify_webhook_ip_whitelist
from config.config import settings

templates = Jinja2Templates(directory="templates")

# Register custom filters
templates.env.filters["timeToStr"] = time_to_str
templates.env.filters["timeDiffNow"] = time_diff_now

router = APIRouter()


# ==================== Public Endpoints (No Authentication) ====================
@router.get("/", response_class=HTMLResponse)
def read_all_logs(
    session: SessionDep,
    request: Request,
    current_user: User = Depends(get_current_user_any_required),
    page: int = 1,
    limit: int = 10,
    show_all: bool = False,
):
    """Get paginated log records (Requires authentication)"""
    # Calculate skip value based on page number
    skip = (page - 1) * limit

    # Build query statement with optional status filter
    statement = select(JMSReqLog)
    if not show_all:
        statement = statement.where(JMSReqLog.status != 200)

    # Get paginated logs with one extra record to check if there are more pages
    statement = (
        statement.order_by(desc(JMSReqLog.updated_at)).offset(skip).limit(limit + 1)
    )
    logs = session.exec(statement).all()

    # Check if there are more pages
    has_next = len(logs) > limit
    if has_next:
        logs = logs[:limit]  # Remove the extra record

    has_prev = page > 1

    return templates.TemplateResponse(
        request=request,
        name="cmdb/show.html",
        context={
            "jobs": logs,
            "current_user": current_user,
            "page_name": "Logs",
            "url": request.url_for("read_all_logs"),
            "current_page": page,
            "has_next": has_next,
            "has_prev": has_prev,
            "limit": limit,
            "show_all": show_all,
        },
    )


@router.post("/", response_model=JMSReqLog)
async def create_log(
    log: JMSReqLogCreate,
    request: Request,
    session: SessionDep,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    x_jms_signature: Optional[str] = Header(None, alias="X-JMS-Signature"),
):
    """Create new log record (Webhook endpoint with security verification)"""
    # Store request body for signature verification
    request._body = await request.body()

    # Verify IP whitelist if configured
    if settings.webhook_ip_whitelist:
        verify_webhook_ip_whitelist(request, settings.webhook_ip_whitelist)

    # Verify webhook authentication if security is configured
    if settings.jms_webhook_api_key or settings.jms_webhook_secret:
        verify_jms_webhook(request, x_api_key, x_jms_signature)

    db_log = JMSReqLog(**log.model_dump())
    session.add(db_log)
    session.commit()
    session.refresh(db_log)
    return db_log


# ==================== User-Level Endpoints (Authentication Required) ====================
@router.get("/list", response_model=JMSReqLogListResponse)
def read_logs_with_pagination(
    session: SessionDep,
    current_user: User = Depends(get_current_user_any_required),
    skip: int = 0,
    limit: int = 100,
):
    """Get paginated log records (Requires authentication)"""
    # Authenticated users can access with reasonable limits
    limit = min(limit, 1000)  # Limit for authenticated users

    statement = (
        select(JMSReqLog).order_by(desc(JMSReqLog.updated_at)).offset(skip).limit(limit)
    )
    logs = session.exec(statement).all()

    return {
        "logs": logs,
        "user": current_user.username,
        "limit": limit,
    }


@router.get("/{log_id}", response_model=JMSReqLog)
def read_log_by_id(
    log_id: int,
    session: SessionDep,
    current_user: User = Depends(get_current_user_any_required),
):
    """Get single log record by ID (Requires authentication via JWT or Session)"""
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
    """Update log record (Requires admin role)"""
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
    """Delete log record (Requires admin role)"""
    log = session.get(JMSReqLog, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")

    session.delete(log)
    session.commit()
    return {"message": "Log deleted successfully", "deleted_by": current_user.username}
