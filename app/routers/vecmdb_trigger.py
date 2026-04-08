from fastapi import APIRouter, Depends, Request, HTTPException, Header
from fastapi.responses import HTMLResponse, JSONResponse
from sqlmodel import select, desc
from typing import Optional, List

from app.models.vecmdb_trigger_models import (
    ProxyResponse,
    PrometheusTarget,
)
from app.models.vecmdb_trigger_reqlog import VecmdbTriggerReqLog
from app.dependencies import (
    SessionDep,
    get_current_user_any_required,
    get_current_user_web_required,
    User,
)
from app.services.vecmdb_trigger_service import (
    vecmdb_trigger_service,
    get_cmdb_trigger_targets,
    get_prometheus_sd_configs,
)
from app.services.vecmdb_prometheus_service import vecmdb_prometheus_service
from app.services.vecmdb_prometheus_auth import authenticate_request
from app.utils.webhook_security import (
    verify_vecmdb_trigger_webhook,
    verify_webhook_ip_whitelist,
)
from app.utils.templates import create_templates
from config.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

templates = create_templates()

router = APIRouter()


def get_client_ip(request: Request) -> str:
    """Extract client IP from request"""
    # Check for forwarded IP first (in case behind proxy)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    # Check for real IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fall back to client host
    if request.client:
        return request.client.host

    return "unknown"


# =============================================================================
# Web UI Endpoints
# =============================================================================


@router.get("/", response_class=HTMLResponse)
def vecmdb_trigger_logs_page(
    session: SessionDep,
    request: Request,
    current_user: User = Depends(get_current_user_web_required),
    page: int = 1,
    limit: int = 20,
    target_name: Optional[str] = None,
):
    """veCMDB Trigger logs page (HTML, requires authentication)"""
    skip = (page - 1) * limit

    statement = select(VecmdbTriggerReqLog)
    if target_name:
        statement = statement.where(
            VecmdbTriggerReqLog.target_name == target_name
        )
    statement = (
        statement.order_by(desc(VecmdbTriggerReqLog.updated_at))
        .offset(skip)
        .limit(limit + 1)
    )
    logs = session.exec(statement).all()

    has_next = len(logs) > limit
    if has_next:
        logs = logs[:limit]
    has_prev = page > 1

    # Get available targets for filter dropdown
    targets = get_cmdb_trigger_targets()

    return templates.TemplateResponse(
        request=request,
        name="vecmdb_trigger/logs.html",
        context={
            "logs": logs,
            "current_user": current_user,
            "page_name": "veCMDB Trigger Logs",
            "url": request.url_for("vecmdb_trigger_logs_page"),
            "current_page": page,
            "has_next": has_next,
            "has_prev": has_prev,
            "limit": limit,
            "filter_target": target_name,
            "available_targets": list(targets.keys()),
        },
    )


# =============================================================================
# CMDB Trigger Endpoints
# =============================================================================


@router.post("/jms/{target_name}")
async def handle_cmdb_trigger(
    target_name: str,
    request: Request,
    session: SessionDep,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """
    Handle incoming CMDB trigger requests from veops for specific target

    This endpoint receives CMDB trigger requests, validates the target name,
    transforms them using target-specific configuration, and forwards them
    to the configured target endpoint.
    """
    # Verify IP whitelist
    verify_webhook_ip_whitelist(request, settings.webhook_ip_whitelist)

    # Verify API key
    verify_vecmdb_trigger_webhook(request, x_api_key)

    # Parse raw JSON body
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON in request body")

    request_id = body.get("id", "unknown")
    client_ip = get_client_ip(request)
    logger.info(
        f"Received CMDB trigger request for target '{target_name}' "
        f"from {client_ip}: {request_id}"
    )

    try:
        response = await vecmdb_trigger_service.process_cmdb_request(
            body, client_ip, target_name, session
        )

        logger.info(
            f"Successfully handled CMDB trigger request for target '{target_name}': "
            f"{request_id}"
        )
        return JSONResponse(
            status_code=response.statuscode,
            content=response.model_dump(),
        )

    except HTTPException:
        raise

    except Exception as e:
        error_msg = (
            f"Internal server error processing request {request_id} "
            f"for target '{target_name}': {str(e)}"
        )
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/status")
async def get_proxy_status():
    """Get proxy service status and configuration info"""
    targets = get_cmdb_trigger_targets()
    prometheus_configs = get_prometheus_sd_configs()

    status_info = {
        "service": "vecmdb-trigger-proxy",
        "status": "running",
        "available_targets": list(targets.keys()),
        "total_targets": len(targets),
        "available_prometheus_configs": list(prometheus_configs.keys()),
        "total_prometheus_configs": len(prometheus_configs),
    }

    logger.info("Proxy status requested")
    return status_info


@router.get("/targets")
async def get_available_targets():
    """Get list of available CMDB trigger targets with their basic info"""
    targets = get_cmdb_trigger_targets()

    targets_info = {}
    for target_name, target_config in targets.items():
        targets_info[target_name] = {
            "target_api_base_url": target_config.get("target_api_base_url"),
            "target_api_path": target_config.get("target_api_path"),
            "target_api_method": target_config.get("target_api_method"),
        }

    logger.info("Available targets list requested")
    return {
        "total_targets": len(targets_info),
        "targets": targets_info,
    }


# =============================================================================
# Request Log Endpoints
# =============================================================================


@router.get("/logs")
def get_vecmdb_trigger_logs(
    request: Request,
    session: SessionDep,
    current_user: User = Depends(get_current_user_any_required),
    target_name: Optional[str] = None,
    skip: int = 0,
    limit: int = 10,
):
    """Get veCMDB Trigger request logs (Requires authentication)"""
    limit = min(limit, 1000)

    # Build query with optional target_name filter
    statement = select(VecmdbTriggerReqLog)
    if target_name:
        statement = statement.where(
            VecmdbTriggerReqLog.target_name == target_name
        )
    statement = (
        statement.offset(skip)
        .limit(limit + 1)
        .order_by(VecmdbTriggerReqLog.updated_at.desc())
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
def get_vecmdb_trigger_log(
    log_id: int,
    session: SessionDep,
    current_user: User = Depends(get_current_user_any_required),
):
    """Get single veCMDB Trigger request log by ID (Requires authentication)"""
    log = session.get(VecmdbTriggerReqLog, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    return log


# =============================================================================
# Prometheus Service Discovery Endpoints
# =============================================================================


@router.get(
    "/prometheus/sd/{config_name}", response_model=List[PrometheusTarget]
)
async def get_prometheus_sd_config(config_name: str, request: Request):
    """
    Generate Prometheus HTTP service discovery configuration

    This endpoint fetches CI data from CMDB using the specified configuration,
    transforms it to Prometheus service discovery format, and returns target groups
    with appropriate labels for monitoring.
    """
    # Check authentication for this specific config
    await authenticate_request(request, config_name)

    logger.info(f"Received Prometheus SD config request for '{config_name}'")

    try:
        prometheus_targets = (
            await vecmdb_prometheus_service.get_prometheus_sd_config(config_name)
        )

        logger.info(
            f"Successfully generated Prometheus SD config for '{config_name}' "
            f"with {len(prometheus_targets)} target groups"
        )
        return prometheus_targets

    except HTTPException:
        raise

    except Exception as e:
        error_msg = (
            f"Internal server error generating Prometheus SD config "
            f"for '{config_name}': {str(e)}"
        )
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/prometheus/configs")
async def get_available_prometheus_configs():
    """Get list of available Prometheus service discovery configurations"""
    configs = get_prometheus_sd_configs()

    configs_info = {}
    for config_name, config_data in configs.items():
        configs_info[config_name] = {
            "cmdb_api_base_url": config_data.get("cmdb_api_base_url"),
            "cmdb_api_path": config_data.get("cmdb_api_path"),
            "target_port": config_data.get("target_port"),
            "target_field": config_data.get("target_field"),
        }

    logger.info("Available Prometheus configs list requested")
    return {
        "total_configs": len(configs_info),
        "configs": configs_info,
    }
