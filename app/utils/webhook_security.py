import hashlib
import hmac
import time
import ipaddress
from fastapi import HTTPException, Header, Request
from typing import Optional, List, Union
from config.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


def verify_cmdb_webhook(
    request: Request,
    api_key: Optional[str] = None,
) -> bool:
    """
    Verify CMDB webhook request using API key verification

    Args:
        request: FastAPI request object
        api_key: API key from X-API-Key header

    Returns:
        bool: True if verification passes

    Raises:
        HTTPException: If verification fails
    """
    # API Key verification
    if api_key:
        expected_api_key = getattr(settings, "cmdb_webhook_api_key", None)
        if expected_api_key and api_key == expected_api_key:
            logger.debug("CMDB webhook verified via API key")
            return True
        else:
            logger.warning(f"Invalid CMDB API key provided: {api_key[:8]}...")
            raise HTTPException(status_code=403, detail="Invalid API key")

    # If no API key provided, reject
    logger.warning("CMDB webhook request without API key")
    raise HTTPException(
        status_code=403,
        detail="Webhook verification required. Provide X-API-Key header",
    )


def verify_feishu_webhook(
    request: Request,
    api_key: Optional[str] = None,
) -> bool:
    """
    Verify Feishu webhook request using API key verification

    Args:
        request: FastAPI request object
        api_key: API key from X-API-Key header

    Returns:
        bool: True if verification passes

    Raises:
        HTTPException: If verification fails
    """
    # API Key verification
    if api_key:
        expected_api_key = getattr(settings, "feishu_webhook_api_key", None)
        if expected_api_key and api_key == expected_api_key:
            logger.debug("Feishu webhook verified via API key")
            return True
        else:
            logger.warning(f"Invalid Feishu API key provided: {api_key[:8]}...")
            raise HTTPException(status_code=403, detail="Invalid API key")

    # If no API key provided, reject
    logger.warning("Feishu webhook request without API key")
    raise HTTPException(
        status_code=403,
        detail="Webhook verification required. Provide X-API-Key header",
    )


def verify_webhook_ip_whitelist(
    request: Request, allowed_ips: List[str] = None
) -> bool:
    """
    Verify webhook request comes from allowed IP addresses or CIDR blocks

    Args:
        request: FastAPI request object
        allowed_ips: List of allowed IP addresses or CIDR blocks (e.g., ["192.168.1.1", "10.0.0.0/8"])

    Returns:
        bool: True if IP is allowed

    Raises:
        HTTPException: If IP is not allowed or invalid IP format
    """
    if not allowed_ips:
        logger.warning("Webhook IP whitelist is empty - rejecting all requests")
        raise HTTPException(
            status_code=403, detail="IP whitelist is empty - access denied"
        )

    # Get client IP from various headers (handle reverse proxy scenarios)
    client_ip = request.client.host
    if "x-forwarded-for" in request.headers:
        client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()
    elif "x-real-ip" in request.headers:
        client_ip = request.headers["x-real-ip"]

    if not client_ip:
        logger.warning("Could not determine client IP address")
        raise HTTPException(status_code=403, detail="Unable to verify client IP")

    try:
        client_ip_obj = ipaddress.ip_address(client_ip)
    except ValueError:
        logger.warning(f"Invalid client IP address format: {client_ip}")
        raise HTTPException(status_code=403, detail="Invalid client IP address")

    # Check against each allowed IP/CIDR in the whitelist
    for allowed_ip in allowed_ips:
        try:
            # Try to parse as network (CIDR) first
            if "/" in allowed_ip:
                network = ipaddress.ip_network(allowed_ip, strict=False)
                if client_ip_obj in network:
                    logger.debug(f"Webhook IP {client_ip} allowed by CIDR {allowed_ip}")
                    return True
            else:
                # Parse as individual IP address
                allowed_ip_obj = ipaddress.ip_address(allowed_ip)
                if client_ip_obj == allowed_ip_obj:
                    logger.debug(f"Webhook IP {client_ip} allowed by exact match")
                    return True
        except ValueError:
            logger.warning(f"Invalid IP/CIDR format in whitelist: {allowed_ip}")
            continue

    logger.warning(f"Webhook IP {client_ip} not in whitelist: {allowed_ips}")
    raise HTTPException(status_code=403, detail="IP address not allowed")
