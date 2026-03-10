from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from app.models.feishu_bot_reqlog import FeishuBotReqLog, FeishuBotReqLogCreate
from app.dependencies import SessionDep
from config.config import settings
from app.utils.webhook_security import (
    verify_feishu_bot_webhook,
    verify_webhook_ip_whitelist,
)
from typing import Dict, Any, Optional
import httpx
import json
import logging

logger = logging.getLogger(__name__)


def log_feishu_bot_request(session: SessionDep, log_entry: FeishuBotReqLogCreate):
    """Log feishu bot request to database and/or console based on configuration"""

    # Console logging
    if settings.enable_console_logging:
        log_message = (
            f"Feishu Bot Webhook - "
            f"ID: {log_entry.webhook_id}, "
            f"Method: {log_entry.method}, "
            f"Path: {log_entry.path}, "
            f"Status: {log_entry.status}, "
            f"Client IP: {log_entry.clientip}"
        )

        if hasattr(log_entry, "error_message") and log_entry.error_message:
            log_message += f", Error: {log_entry.error_message}"
            logger.error(log_message)
        else:
            logger.info(log_message)

    # Database logging
    if settings.enable_database_logging:
        try:
            db_log = FeishuBotReqLog(**log_entry.model_dump())
            session.add(db_log)
            session.commit()
        except Exception as e:
            # If database logging fails and console logging is enabled, log the error
            if settings.enable_console_logging:
                logger.error(f"Failed to save log to database: {str(e)}")


def convert_grafana_to_feishu(grafana_payload: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Grafana alert payload to Feishu interactive card format"""

    # Extract required fields from Grafana payload
    status = grafana_payload.get("status", "unknown")
    title = grafana_payload.get("title", "Alert")
    message = grafana_payload.get("message", "")

    # Map status to Feishu template color
    template_map = {"firing": "red", "resolved": "green", "unknown": "wathet"}
    template = template_map.get(status.lower(), "blue")

    # Build Feishu interactive card payload
    feishu_payload = {
        "msg_type": "interactive",
        "card": {
            "schema": "2.0",
            "header": {
                "template": template,
                "title": {"content": title, "tag": "plain_text"},
            },
            "body": {"elements": [{"tag": "markdown", "content": message}]},
        },
    }

    return feishu_payload


def is_grafana_alert(payload: Dict[str, Any]) -> bool:
    """Check if payload is from Grafana alerting"""
    return (
        isinstance(payload, dict)
        and "status" in payload
        and "title" in payload
        and "message" in payload
    )


async def process_webhook_request(
    webhook_id: str,
    request: Request,
    session: SessionDep,
    api_key: Optional[str] = None,
):
    """Process webhook request with API key verification and forwarding"""

    # Store request body for verification
    request._body = await request.body()

    # Verify IP whitelist (empty list = deny all)
    verify_webhook_ip_whitelist(request, settings.webhook_ip_whitelist)

    # Verify Feishu Bot webhook API key (skip if no API keys configured)
    verify_feishu_bot_webhook(request, api_key)

    # Get client IP
    client_ip = request.client.host
    if "x-forwarded-for" in request.headers:
        client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()
    elif "x-real-ip" in request.headers:
        client_ip = request.headers["x-real-ip"]

    # Get request data
    method = request.method
    path = str(request.url.path)
    query = str(request.url.query) if request.url.query else ""
    headers = dict(request.headers)

    # Read request body
    body_bytes = await request.body()
    try:
        body = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
    except json.JSONDecodeError:
        body = {"raw": body_bytes.decode("utf-8", errors="ignore")}

    # Convert Grafana alert to Feishu format if needed
    original_body = body.copy()
    if is_grafana_alert(body):
        body = convert_grafana_to_feishu(body)

    # Feishu API URL
    feishu_url = f"{settings.feishu_webhook_base_url}{webhook_id}"

    # Initialize log entry with original body for logging
    log_entry = FeishuBotReqLogCreate(
        webhook_id=webhook_id,
        method=method,
        path=path,
        query=query,
        headers=headers,
        body=original_body,  # Log original payload
        clientip=client_ip,
        status=0,  # Will update after response
    )

    try:
        # Forward request to Feishu
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Prepare headers for forwarding (remove host and other proxy headers)
            forward_headers = {
                k: v
                for k, v in headers.items()
                if k.lower()
                not in ["host", "x-forwarded-for", "x-real-ip", "content-length"]
            }

            response = await client.post(
                feishu_url, json=body if body else None, headers=forward_headers
            )

            # Get response data
            response_status = response.status_code
            response_headers = dict(response.headers)

            try:
                response_body = response.json()
            except Exception:
                response_body = {"raw": response.text}

            # Update log entry with response data
            log_entry.status = response_status
            log_entry.response_headers = response_headers
            log_entry.response_body = response_body

            # Save log based on configuration
            log_feishu_bot_request(session, log_entry)

            # Return Feishu response to client
            return JSONResponse(
                content=response_body,
                status_code=response_status,
                headers={
                    k: v
                    for k, v in response_headers.items()
                    if k.lower() not in ["content-length", "transfer-encoding"]
                },
            )

    except httpx.TimeoutException:
        # Handle timeout
        error_msg = "Request to Feishu API timed out"
        log_entry.status = 504
        log_entry.error_message = error_msg

        # Save error log based on configuration
        log_feishu_bot_request(session, log_entry)

        raise HTTPException(status_code=504, detail=error_msg)

    except httpx.RequestError as e:
        # Handle connection errors
        error_msg = f"Failed to connect to Feishu API: {str(e)}"
        log_entry.status = 502
        log_entry.error_message = error_msg

        # Save error log based on configuration
        log_feishu_bot_request(session, log_entry)

        raise HTTPException(status_code=502, detail=error_msg)

    except Exception as e:
        # Handle other errors
        error_msg = f"Internal server error: {str(e)}"
        log_entry.status = 500
        log_entry.error_message = error_msg

        # Save error log based on configuration
        log_feishu_bot_request(session, log_entry)

        raise HTTPException(status_code=500, detail=error_msg)
