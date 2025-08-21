from fastapi import APIRouter, Depends, HTTPException, Request, Header
from fastapi.responses import HTMLResponse
from sqlmodel import select, func, desc
from app.models.cmdb_reqlog import (
    CmdbReqLog,
    CmdbReqLogCreate,
    CmdbReqLogUpdate,
    CmdbReqLogListResponse,
    PaginationUrls,
    PaginationInfo,
)
from app.dependencies import (
    SessionDep,
    get_current_user_flexible,
    get_current_user_any_required,
    get_current_user_web_required,
    require_roles,
    User,
)
from typing import List, Optional
import time
import json
from fastapi.templating import Jinja2Templates
from app.utils.template_filters import time_to_str, time_diff_now
from app.utils.webhook_security import verify_cmdb_webhook, verify_webhook_ip_whitelist
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
    current_user: User = Depends(get_current_user_web_required),
    page: int = 1,
    limit: int = 10,
    show_all: bool = False,
):
    """Get paginated log records (Requires authentication)"""
    # Calculate skip value based on page number
    skip = (page - 1) * limit

    # Build query statement with optional status filter
    statement = select(CmdbReqLog)
    if not show_all:
        statement = statement.where(CmdbReqLog.status != 200)

    # Get paginated logs with one extra record to check if there are more pages
    statement = (
        statement.order_by(desc(CmdbReqLog.updated_at)).offset(skip).limit(limit + 1)
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
            "page_name": "cmdb Logs",
            "url": request.url_for("read_all_logs"),
            "current_page": page,
            "has_next": has_next,
            "has_prev": has_prev,
            "limit": limit,
            "show_all": show_all,
        },
    )


@router.post("/", response_model=CmdbReqLog)
async def create_log(
    request: Request,
    session: SessionDep,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """CMDB proxy endpoint - forwards request and logs response (Webhook endpoint with API key verification)"""

    # Read request body
    body_bytes = await request.body()
    try:
        request_data = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in request body")

    # Process the CMDB proxy request
    from app.services.cmdb_service import process_cmdb_request

    result = await process_cmdb_request(request_data, request, session, x_api_key)

    # Return the logged entry from database
    # Get the most recent log entry for this request
    from sqlmodel import desc

    statement = select(CmdbReqLog).order_by(desc(CmdbReqLog.created_at)).limit(1)
    latest_log = session.exec(statement).first()

    if not latest_log:
        raise HTTPException(status_code=500, detail="Failed to retrieve logged request")

    return latest_log


# ==================== User-Level Endpoints (Authentication Required) ====================
@router.get("/logs", response_model=CmdbReqLogListResponse)
def read_logs_with_pagination(
    request: Request,
    session: SessionDep,
    current_user: User = Depends(get_current_user_any_required),
    skip: int = 0,
    limit: int = 10,
):
    """Get paginated log records (Requires authentication)"""
    # Authenticated users can access with reasonable limits
    limit = min(limit, 1000)  # Protect limit for max records in one page

    # Get logs with pagination (fetch limit+1 to check if there are more records)
    statement = (
        select(CmdbReqLog)
        .order_by(desc(CmdbReqLog.updated_at))
        .offset(skip)
        .limit(limit + 1)
    )
    logs = session.exec(statement).all()

    # Check if there are more records
    has_next = len(logs) > limit
    if has_next:
        logs = logs[:limit]  # Remove the extra record

    has_prev = skip > 0

    # Build base URL with reverse proxy support
    def get_base_url() -> str:
        # Check for reverse proxy headers
        proto = request.headers.get("x-forwarded-proto", "http")
        host = request.headers.get("x-forwarded-host") or request.headers.get(
            "host", "localhost:8000"
        )

        # Remove port from host if it's standard port
        if (proto == "https" and host.endswith(":443")) or (
            proto == "http" and host.endswith(":80")
        ):
            host = host.rsplit(":", 1)[0]

        return f"{proto}://{host}{request.url.path}"

    base_url = get_base_url()

    # Generate pagination URLs
    pagination_urls = {
        "current": f"{base_url}?skip={skip}&limit={limit}",
    }

    if has_prev:
        prev_skip = max(0, skip - limit)
        pagination_urls["prev"] = f"{base_url}?skip={prev_skip}&limit={limit}"

    if has_next:
        next_skip = skip + limit
        pagination_urls["next"] = f"{base_url}?skip={next_skip}&limit={limit}"

    return {
        "logs": logs,
        "user": current_user.username,
        "limit": limit,
        "pagination": PaginationInfo(
            per_page=limit,
            has_next=has_next,
            has_prev=has_prev,
            urls=PaginationUrls(**pagination_urls),
        ),
    }


@router.get("/{log_id}", response_model=CmdbReqLog)
def read_log_by_id(
    log_id: int,
    session: SessionDep,
    current_user: User = Depends(get_current_user_any_required),
):
    """Get single log record by ID (Requires authentication via JWT or Session)"""
    log = session.get(CmdbReqLog, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    return log


# ==================== Admin-Level Endpoints (Role-based Access Control) ====================
@router.put("/{log_id}", response_model=CmdbReqLog)
def update_log(
    log_id: int,
    update: CmdbReqLogUpdate,
    session: SessionDep,
    current_user: User = Depends(require_roles("admin")),
):
    """Update log record (Requires admin role)"""
    log = session.get(CmdbReqLog, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")

    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(log, key, value)

    # Set author to current logged-in user (browser operation)
    log.author = current_user.username
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
    log = session.get(CmdbReqLog, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")

    session.delete(log)
    session.commit()
    return {"message": "Log deleted successfully", "deleted_by": current_user.username}
