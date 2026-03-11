from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlmodel import select
from app.models.gitlab_hook_reqlog import GitlabHookReqLog
from app.dependencies import SessionDep, get_current_user_any_required, User
from app.services.gitlab_hook_service import process_gitlab_hook_webhook
from typing import Optional

router = APIRouter()


@router.post("/webhook")
async def gitlab_hook_webhook(
    request: Request,
    session: SessionDep,
    x_gitlab_token: Optional[str] = Header(None, alias="X-Gitlab-Token"),
    x_gitlab_event: Optional[str] = Header(None, alias="X-Gitlab-Event"),
):
    """
    GitLab System Hook endpoint.

    Receives GitLab System Hooks and forwards them to Jenkins Generic Webhook Trigger.

    Headers:
        X-Gitlab-Token: GitLab secret token for authentication
        X-Gitlab-Event: GitLab event type (e.g., "Push Hook", "Tag Push Hook")

    Currently supported events:
        - Push events (gitlab_hook_enable_push_events)

    Reserved for future support:
        - Tag Push events (gitlab_hook_enable_tag_push_events)
        - Merge Request events (gitlab_hook_enable_merge_request_events)
    """
    return await process_gitlab_hook_webhook(
        request,
        session,
        x_gitlab_token,
        x_gitlab_event,
    )


@router.get("/logs")
def get_gitlab_hook_logs(
    request: Request,
    session: SessionDep,
    current_user: User = Depends(get_current_user_any_required),
    skip: int = 0,
    limit: int = 10,
):
    """Get GitLab Hook webhook logs (Requires authentication)"""
    limit = min(limit, 1000)  # Protect limit for max records in one page

    # Get logs with pagination (fetch limit+1 to check if there are more records)
    statement = (
        select(GitlabHookReqLog)
        .offset(skip)
        .limit(limit + 1)
        .order_by(GitlabHookReqLog.updated_at.desc())
    )
    logs = session.exec(statement).all()

    # Check if there are more records
    has_next = len(logs) > limit
    if has_next:
        logs = logs[:limit]

    has_prev = skip > 0

    # Build base URL with reverse proxy support
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
def get_gitlab_hook_log(
    log_id: int,
    session: SessionDep,
    current_user: User = Depends(get_current_user_any_required),
):
    """Get single GitLab Hook webhook log by ID (Requires authentication)"""
    log = session.get(GitlabHookReqLog, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    return log
