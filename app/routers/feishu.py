from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlmodel import select
from app.models.feishu_reqlog import FeishuReqLog
from app.dependencies import SessionDep, get_current_user_any_required, User
from app.services.webhook_mapping import get_webhook_id_by_name
from app.services.feishu_service import process_webhook_request
from typing import Optional

router = APIRouter()


@router.post("/webhook/proxy/{webhook_id}")
async def feishu_webhook_proxy(
    webhook_id: str,
    request: Request,
    session: SessionDep,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """Feishu webhook proxy endpoint using webhook ID (with API key verification)"""
    return await process_webhook_request(
        webhook_id,
        request,
        session,
        x_api_key,
    )


@router.post("/webhook/alias/{webhook_name}")
async def feishu_webhook_alias(
    webhook_name: str,
    request: Request,
    session: SessionDep,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """Feishu webhook proxy endpoint using webhook name alias (with API key verification)"""
    # Get webhook ID from name mapping
    webhook_id = get_webhook_id_by_name(webhook_name)
    if not webhook_id:
        raise HTTPException(
            status_code=404,
            detail=f"Webhook name '{webhook_name}' not found in configuration",
        )

    return await process_webhook_request(
        webhook_id,
        request,
        session,
        x_api_key,
    )


@router.get("/logs")
def get_feishu_logs(
    request: Request,
    session: SessionDep,
    current_user: User = Depends(get_current_user_any_required),
    skip: int = 0,
    limit: int = 10,
):
    limit = min(limit, 1000)  # Protect limit for max records in one page

    """Get Feishu webhook logs (Requires authentication)"""
    # Get logs with pagination (fetch limit+1 to check if there are more records)
    statement = (
        select(FeishuReqLog)
        .offset(skip)
        .limit(limit + 1)
        .order_by(FeishuReqLog.updated_at.desc())
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
        "data": logs,
        "pagination": {
            "per_page": limit,
            "has_next": has_next,
            "has_prev": has_prev,
            "urls": pagination_urls,
        },
    }


@router.get("/logs/{log_id}")
def get_feishu_log(
    log_id: int,
    session: SessionDep,
    current_user: User = Depends(get_current_user_any_required),
):
    """Get single Feishu webhook log by ID (Requires authentication)"""
    log = session.get(FeishuReqLog, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    return log
