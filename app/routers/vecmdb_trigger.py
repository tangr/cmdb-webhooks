from fastapi import APIRouter, Request, HTTPException, Header
from fastapi.responses import JSONResponse
from typing import Optional, List

from app.models.vecmdb_trigger_models import (
    CMDBTriggerRequest,
    ProxyResponse,
    PrometheusTarget,
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
from config.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

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
# CMDB Trigger Endpoints
# =============================================================================


@router.post("/jms/{target_name}")
async def handle_cmdb_trigger(
    target_name: str,
    cmdb_request: CMDBTriggerRequest,
    request: Request,
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

    client_ip = get_client_ip(request)
    logger.info(
        f"Received CMDB trigger request for target '{target_name}' "
        f"from {client_ip}: {cmdb_request.id}"
    )

    try:
        response = await vecmdb_trigger_service.process_cmdb_request(
            cmdb_request, client_ip, target_name
        )

        logger.info(
            f"Successfully handled CMDB trigger request for target '{target_name}': "
            f"{cmdb_request.id}"
        )
        return JSONResponse(
            status_code=response.statuscode,
            content=response.model_dump(),
        )

    except HTTPException:
        raise

    except Exception as e:
        error_msg = (
            f"Internal server error processing request {cmdb_request.id} "
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
