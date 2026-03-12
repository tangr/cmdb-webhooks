"""
Feishu Approval API router.

This router provides endpoints for:
- Creating approval instances
- Querying approval status
- Listing approval records
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.dependencies import (
    SessionDep,
    User,
    get_current_user_any_required,
)
from app.services.feishu_approval_service import FeishuApprovalService

router = APIRouter()


# ==================== Request/Response Models ====================
class CreateApprovalRequest(BaseModel):
    """Request model for creating an approval"""

    app_name: str = Field(
        default="default", description="Feishu app name from config"
    )
    feishu_user_id: str = Field(..., description="Feishu user ID (short format)")
    form_data: Dict[str, Any] = Field(..., description="Form data for approval")
    approval_code: Optional[str] = Field(
        default=None, description="Approval code (uses default from config if not provided)"
    )


class ApprovalResponse(BaseModel):
    """Standard API response"""

    status: int = Field(default=0, description="Status code (0=success)")
    msg: str = Field(default="success", description="Response message")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Response data")


# ==================== API Endpoints ====================
@router.get("/apps")
async def get_available_apps(
    current_user: User = Depends(get_current_user_any_required),
) -> ApprovalResponse:
    """
    Get list of available Feishu apps.
    Requires authentication.
    """
    apps = FeishuApprovalService.get_available_apps()
    return ApprovalResponse(data={"apps": apps})


@router.post("/create")
async def create_approval(
    request: Request,
    body: CreateApprovalRequest,
    session: SessionDep,
    current_user: User = Depends(get_current_user_any_required),
) -> ApprovalResponse:
    """
    Create a new approval instance in Feishu.
    Requires authentication.

    The approval will be created using the specified Feishu app configuration.
    Form data will be submitted to Feishu as approval form fields.
    """
    # Get client IP
    client_ip = request.client.host
    if "x-forwarded-for" in request.headers:
        client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()
    elif "x-real-ip" in request.headers:
        client_ip = request.headers["x-real-ip"]

    try:
        result = await FeishuApprovalService.create_approval(
            session=session,
            app_name=body.app_name,
            feishu_user_id=body.feishu_user_id,
            form_data=body.form_data,
            username=current_user.username,
            clientip=client_ip,
            approval_code=body.approval_code,
        )
        return ApprovalResponse(msg="Approval created successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create approval: {str(e)}")


@router.get("/status/{log_id}")
async def get_approval_status_by_id(
    log_id: int,
    session: SessionDep,
    current_user: User = Depends(get_current_user_any_required),
) -> ApprovalResponse:
    """
    Get approval status by database log ID.
    Requires authentication.

    This will query Feishu API to get the latest status and update the local record.
    """
    try:
        result = await FeishuApprovalService.get_approval_status(
            session=session, log_id=log_id
        )
        return ApprovalResponse(data=result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get approval status: {str(e)}")


@router.get("/status/instance/{instance_code}")
async def get_approval_status_by_instance(
    instance_code: str,
    session: SessionDep,
    app_name: str = "default",
    current_user: User = Depends(get_current_user_any_required),
) -> ApprovalResponse:
    """
    Get approval status by Feishu instance code.
    Requires authentication.

    This will query Feishu API directly using the instance code.
    """
    try:
        result = await FeishuApprovalService.get_approval_status_by_instance_code(
            session=session, instance_code=instance_code, app_name=app_name
        )
        return ApprovalResponse(data=result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get approval status: {str(e)}")


@router.get("/logs")
def get_approval_logs(
    request: Request,
    session: SessionDep,
    current_user: User = Depends(get_current_user_any_required),
    username: Optional[str] = None,
    app_name: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> ApprovalResponse:
    """
    List approval records with optional filters.
    Requires authentication.

    Filters:
    - username: Filter by the user who created the approval
    - app_name: Filter by Feishu app name
    - status: Filter by approval status (pending, approved, rejected, canceled)
    """
    limit = min(limit, 1000)  # Protect limit for max records in one page

    result = FeishuApprovalService.list_approvals(
        session=session,
        username=username,
        app_name=app_name,
        status=status,
        limit=limit,
        offset=skip,
    )

    # Build pagination URLs
    def get_base_url() -> str:
        proto = request.headers.get("x-forwarded-proto", "http")
        host = request.headers.get("x-forwarded-host") or request.headers.get(
            "host", "localhost:8000"
        )
        if (proto == "https" and host.endswith(":443")) or (
            proto == "http" and host.endswith(":80")
        ):
            host = host.rsplit(":", 1)[0]
        return f"{proto}://{host}{request.url.path}"

    base_url = get_base_url()

    # Build query params
    query_parts = []
    if username:
        query_parts.append(f"username={username}")
    if app_name:
        query_parts.append(f"app_name={app_name}")
    if status:
        query_parts.append(f"status={status}")

    query_prefix = "&".join(query_parts)
    if query_prefix:
        query_prefix = f"{query_prefix}&"

    has_next = result["total"] == limit
    has_prev = skip > 0

    pagination_urls = {
        "current": f"{base_url}?{query_prefix}skip={skip}&limit={limit}",
    }

    if has_prev:
        prev_skip = max(0, skip - limit)
        pagination_urls["prev"] = f"{base_url}?{query_prefix}skip={prev_skip}&limit={limit}"

    if has_next:
        next_skip = skip + limit
        pagination_urls["next"] = f"{base_url}?{query_prefix}skip={next_skip}&limit={limit}"

    return ApprovalResponse(
        data={
            "records": result["records"],
            "pagination": {
                "total": result["total"],
                "per_page": limit,
                "has_next": has_next,
                "has_prev": has_prev,
                "urls": pagination_urls,
            },
        }
    )


@router.get("/logs/{log_id}")
def get_approval_log(
    log_id: int,
    session: SessionDep,
    current_user: User = Depends(get_current_user_any_required),
) -> ApprovalResponse:
    """
    Get a single approval record by ID.
    Requires authentication.
    """
    log = FeishuApprovalService.get_approval_by_id(session=session, log_id=log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Approval log not found")

    return ApprovalResponse(data=log.model_dump())
