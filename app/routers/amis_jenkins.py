from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlmodel import select
from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.models.amis_jenkins_reqlog import AmisJenkinsReqLog
from app.models.pending_jenkins_job import PendingJenkinsJob
from app.dependencies import (
    SessionDep,
    get_current_user_web_required,
    get_current_user_any_required,
    User,
)
from app.services.amis_jenkins_service import (
    get_form_config,
    get_all_forms,
    get_form_schema,
    process_form_submit,
    get_pending_jobs,
    sync_pending_job_status,
    execute_pending_job,
)
from app.utils.template_filters import time_to_str, time_diff_now
import json

router = APIRouter()


# ==================== Request Models ====================
class ExecuteJobRequest(BaseModel):
    """Request body for executing a pending job with optional modified fields."""

    modified_fields: Optional[Dict[str, Any]] = None


# Setup templates
templates = Jinja2Templates(directory="templates")
templates.env.filters["timeToStr"] = time_to_str
templates.env.filters["timeDiffNow"] = time_diff_now


# ==================== HTML Pages ====================
@router.get("/forms", response_class=HTMLResponse)
async def forms_list_page(
    request: Request,
    current_user: User = Depends(get_current_user_web_required),
):
    """
    Display list of available Amis forms.
    Requires web authentication.
    """
    forms = get_all_forms()
    return templates.TemplateResponse(
        "amis_jenkins/forms.html",
        {
            "request": request,
            "page_name": "Amis Jenkins Forms",
            "current_user": current_user,
            "forms": forms,
        },
    )


@router.get("/forms/{form_id}", response_class=HTMLResponse)
async def form_page(
    request: Request,
    form_id: str,
    current_user: User = Depends(get_current_user_web_required),
):
    """
    Display Amis form page for a specific form.
    Requires web authentication.
    """
    form_config = get_form_config(form_id)
    if not form_config:
        raise HTTPException(status_code=404, detail=f"Form not found: {form_id}")

    schema = form_config.get("schema", {})

    return templates.TemplateResponse(
        "amis_jenkins/form.html",
        {
            "request": request,
            "page_name": form_config.get("title", form_id),
            "current_user": current_user,
            "form_id": form_id,
            "form_title": form_config.get("title", form_id),
            "form_description": form_config.get("description", ""),
            "form_schema": json.dumps(schema, ensure_ascii=False),
        },
    )


# ==================== API Endpoints ====================
@router.get("/api/forms")
async def api_get_forms(
    current_user: User = Depends(get_current_user_any_required),
):
    """
    Get list of all available forms.
    Requires authentication.
    """
    forms = get_all_forms()
    return {"status": 0, "msg": "success", "data": forms}


@router.get("/api/schema/{form_id}")
async def api_get_form_schema(
    form_id: str,
    current_user: User = Depends(get_current_user_any_required),
):
    """
    Get Amis schema for a specific form.
    Requires authentication.
    """
    schema = get_form_schema(form_id)
    if not schema:
        raise HTTPException(status_code=404, detail=f"Form not found: {form_id}")

    return {"status": 0, "msg": "success", "data": schema}


@router.post("/api/submit/{form_id}")
async def api_submit_form(
    request: Request,
    form_id: str,
    session: SessionDep,
    current_user: User = Depends(get_current_user_any_required),
):
    """
    Submit form data to Jenkins.
    Requires authentication.

    The form data is forwarded to Jenkins based on the trigger_type:
    - generic_webhook: POST to Jenkins Generic Webhook Trigger
    - remote_api: POST to Jenkins buildWithParameters API
    """
    return await process_form_submit(request, session, form_id, current_user)


# ==================== Log Endpoints ====================
@router.get("/logs")
def get_amis_jenkins_logs(
    request: Request,
    session: SessionDep,
    current_user: User = Depends(get_current_user_any_required),
    form_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 10,
):
    """Get Amis Jenkins logs with pagination (Requires authentication)"""
    limit = min(limit, 1000)  # Protect limit for max records in one page

    # Get logs with pagination (fetch limit+1 to check if there are more records)
    statement = select(AmisJenkinsReqLog)
    if form_id:
        statement = statement.where(AmisJenkinsReqLog.form_id == form_id)
    statement = (
        statement.offset(skip)
        .limit(limit + 1)
        .order_by(AmisJenkinsReqLog.updated_at.desc())
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
def get_amis_jenkins_log(
    log_id: int,
    session: SessionDep,
    current_user: User = Depends(get_current_user_any_required),
):
    """Get single Amis Jenkins log by ID (Requires authentication)"""
    log = session.get(AmisJenkinsReqLog, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    return log


# ==================== Pending Jobs (with Approval) ====================
@router.get("/pending", response_class=HTMLResponse)
async def pending_jobs_page(
    request: Request,
    current_user: User = Depends(get_current_user_web_required),
):
    """
    Display pending Jenkins jobs page.
    Requires web authentication.
    """
    return templates.TemplateResponse(
        "amis_jenkins/pending.html",
        {
            "request": request,
            "page_name": "Pending Jenkins Jobs",
            "current_user": current_user,
        },
    )


@router.get("/api/pending")
def api_get_pending_jobs(
    session: SessionDep,
    current_user: User = Depends(get_current_user_any_required),
    username: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
):
    """
    Get list of pending Jenkins jobs.
    Requires authentication.

    Query parameters:
    - username: Filter by username (default: None for all users)
    - status: Filter by status (pending_approval, approved, executed, rejected, canceled)
    - skip: Offset for pagination
    - limit: Max records to return
    """
    limit = min(limit, 100)
    jobs = get_pending_jobs(
        session=session,
        username=username,
        status=status,
        limit=limit,
        offset=skip,
    )
    return {"status": 0, "msg": "success", "data": jobs}


@router.get("/api/pending/{job_id}")
def api_get_pending_job(
    job_id: int,
    session: SessionDep,
    current_user: User = Depends(get_current_user_any_required),
):
    """
    Get a single pending job by ID.
    Requires authentication.
    """
    job = session.get(PendingJenkinsJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Pending job not found")
    return {"status": 0, "msg": "success", "data": job}


@router.post("/api/pending/{job_id}/sync")
async def api_sync_pending_job(
    job_id: int,
    session: SessionDep,
    current_user: User = Depends(get_current_user_any_required),
):
    """
    Sync pending job status from Feishu approval.
    Requires authentication.
    """
    try:
        result = await sync_pending_job_status(session, job_id)
        return {"status": 0, "msg": "Status synced successfully", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to sync status: {str(e)}")


@router.post("/api/pending/{job_id}/execute")
async def api_execute_pending_job(
    job_id: int,
    session: SessionDep,
    current_user: User = Depends(get_current_user_any_required),
    body: Optional[ExecuteJobRequest] = None,
):
    """
    Execute a pending Jenkins job after approval.
    Requires authentication.

    The job must be in 'approved' status to be executed.

    Request body (optional):
    - modified_fields: Dict of field values to override (must be in modifiable_fields list)

    Multi-execution support:
    - Jobs with max_executions > 0 can be executed multiple times
    - Jobs with expire_at > 0 have time-based expiration
    - Status remains 'approved' until exhausted or expired
    """
    try:
        modified_fields = body.modified_fields if body else None
        result = await execute_pending_job(session, job_id, modified_fields)
        if result["success"]:
            return {
                "status": 0,
                "msg": "Jenkins build triggered successfully",
                "data": result,
            }
        else:
            return {
                "status": 1,
                "msg": f"Jenkins build trigger failed with status {result['jenkins_status']}",
                "data": result,
            }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to execute job: {str(e)}"
        )
