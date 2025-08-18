from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlmodel import select, func
from app.models.feishu_reqlog import FeishuReqLog, FeishuReqLogCreate
from app.dependencies import SessionDep
from config.config import settings
from app.services.webhook_mapping import get_webhook_id_by_name
from typing import Dict, Any
import httpx
import json
import time
import math

router = APIRouter()


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


async def _process_webhook_request(
    webhook_id: str,
    request: Request,
    session: SessionDep,
):
    """Internal function to process webhook request"""

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
    log_entry = FeishuReqLogCreate(
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
            except:
                response_body = {"raw": response.text}

            # Update log entry with response data
            log_entry.status = response_status
            log_entry.response_headers = response_headers
            log_entry.response_body = response_body

            # Save to database
            db_log = FeishuReqLog(**log_entry.model_dump())
            session.add(db_log)
            session.commit()

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

        # Save error to database
        db_log = FeishuReqLog(**log_entry.model_dump())
        session.add(db_log)
        session.commit()

        raise HTTPException(status_code=504, detail=error_msg)

    except httpx.RequestError as e:
        # Handle connection errors
        error_msg = f"Failed to connect to Feishu API: {str(e)}"
        log_entry.status = 502
        log_entry.error_message = error_msg

        # Save error to database
        db_log = FeishuReqLog(**log_entry.model_dump())
        session.add(db_log)
        session.commit()

        raise HTTPException(status_code=502, detail=error_msg)

    except Exception as e:
        # Handle other errors
        error_msg = f"Internal server error: {str(e)}"
        log_entry.status = 500
        log_entry.error_message = error_msg

        # Save error to database
        db_log = FeishuReqLog(**log_entry.model_dump())
        session.add(db_log)
        session.commit()

        raise HTTPException(status_code=500, detail=error_msg)


@router.post("/webhook/proxy/{webhook_id}")
async def feishu_webhook_proxy(
    webhook_id: str,
    request: Request,
    session: SessionDep,
):
    """Feishu webhook proxy endpoint using webhook ID"""
    return await _process_webhook_request(webhook_id, request, session)


@router.post("/webhook/alias/{webhook_name}")
async def feishu_webhook_alias(
    webhook_name: str,
    request: Request,
    session: SessionDep,
):
    """Feishu webhook proxy endpoint using webhook name alias"""
    # Get webhook ID from name mapping
    webhook_id = get_webhook_id_by_name(webhook_name)
    if not webhook_id:
        raise HTTPException(
            status_code=404,
            detail=f"Webhook name '{webhook_name}' not found in configuration",
        )

    return await _process_webhook_request(webhook_id, request, session)


@router.get("/logs")
def get_feishu_logs(
    request: Request, session: SessionDep, skip: int = 0, limit: int = 10
):
    """Get Feishu webhook logs"""
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
def get_feishu_log(log_id: int, session: SessionDep):
    """Get single Feishu webhook log by ID"""
    log = session.get(FeishuReqLog, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    return log
