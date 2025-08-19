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
    signature: Optional[str] = None,
) -> bool:
    """
    Verify CMDB webhook request using API key or signature verification

    Args:
        request: FastAPI request object
        api_key: API key from X-API-Key header
        signature: Signature from X-CMDB-Signature header

    Returns:
        bool: True if verification passes

    Raises:
        HTTPException: If verification fails
    """
    # Method 1: API Key verification (simple but effective)
    if api_key:
        expected_api_key = getattr(settings, "cmdb_webhook_api_key", None)
        if expected_api_key and api_key == expected_api_key:
            logger.debug("CMDB webhook verified via API key")
            return True
        else:
            logger.warning(f"Invalid CMDB API key provided: {api_key[:8]}...")
            raise HTTPException(status_code=403, detail="Invalid API key")

    # Method 2: Signature verification (more secure)
    if signature:
        # This would require implementing HMAC signature verification
        # For now, we'll implement a basic version
        secret = getattr(settings, "cmdb_webhook_secret", None)
        if secret:
            # Create expected signature based on request body
            body = request._body if hasattr(request, "_body") else b""
            expected_signature = hmac.new(
                secret.encode("utf-8"), body, hashlib.sha256
            ).hexdigest()

            if hmac.compare_digest(signature, expected_signature):
                logger.debug("CMDB webhook verified via signature")
                return True
            else:
                logger.warning("Invalid CMDB webhook signature")
                raise HTTPException(status_code=403, detail="Invalid signature")

    # If no verification method provided, reject
    logger.warning("CMDB webhook request without proper verification")
    raise HTTPException(
        status_code=403,
        detail="Webhook verification required. Provide X-API-Key or X-CMDB-Signature header",
    )


def verify_feishu_webhook(
    request: Request,
    timestamp: Optional[str] = None,
    nonce: Optional[str] = None,
    signature: Optional[str] = None,
) -> bool:
    """
    Verify Feishu webhook request using official signature verification

    Args:
        request: FastAPI request object
        timestamp: Request timestamp from X-Lark-Request-Timestamp header
        nonce: Request nonce from X-Lark-Request-Nonce header
        signature: Request signature from X-Lark-Signature header

    Returns:
        bool: True if verification passes

    Raises:
        HTTPException: If verification fails
    """
    # Check if Feishu webhook verification is enabled
    feishu_secret = getattr(settings, "feishu_webhook_secret", None)

    if not feishu_secret:
        # If no secret configured, allow request but log warning
        logger.warning("Feishu webhook secret not configured, skipping verification")
        return True

    # Require all verification parameters
    if not all([timestamp, nonce, signature]):
        logger.warning("Missing required Feishu webhook headers")
        raise HTTPException(
            status_code=403,
            detail="Missing required headers: X-Lark-Request-Timestamp, X-Lark-Request-Nonce, X-Lark-Signature",
        )

    # Verify timestamp (prevent replay attacks)
    try:
        request_time = int(timestamp)
        current_time = int(time.time())

        # Allow 5 minute window
        if abs(current_time - request_time) > 300:
            logger.warning(f"Feishu webhook timestamp too old: {timestamp}")
            raise HTTPException(status_code=403, detail="Request timestamp too old")

    except ValueError:
        logger.warning(f"Invalid Feishu webhook timestamp: {timestamp}")
        raise HTTPException(status_code=403, detail="Invalid timestamp format")

    # Create signature string according to Feishu documentation
    body = request._body if hasattr(request, "_body") else b""
    sign_string = f"{timestamp}{nonce}{body.decode('utf-8')}"

    # Calculate expected signature
    expected_signature = hmac.new(
        feishu_secret.encode("utf-8"), sign_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    # Verify signature
    if hmac.compare_digest(signature, expected_signature):
        logger.debug("Feishu webhook verified successfully")
        return True
    else:
        logger.warning("Invalid Feishu webhook signature")
        raise HTTPException(status_code=403, detail="Invalid signature")


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
