from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from app.models.cmdb_trigger_reqlog import CmdbTriggerReqLog, CmdbTriggerReqLogCreate
from app.dependencies import SessionDep
from config.config import settings
from app.utils.webhook_security import (
    verify_cmdb_trigger_webhook,
    verify_webhook_ip_whitelist,
)
from typing import Dict, Any, Optional
import httpx
import json
import logging
import time

logger = logging.getLogger(__name__)


def log_cmdb_trigger_request(session: SessionDep, log_entry: CmdbTriggerReqLogCreate):
    """Log CMDB Trigger request to database based on configuration"""

    # Database logging
    if settings.enable_database_logging:
        try:
            db_log = CmdbTriggerReqLog(**log_entry.model_dump())
            session.add(db_log)
            session.commit()
        except Exception as e:
            # If database logging fails and console logging is enabled, log the error
            if settings.enable_console_logging:
                logger.error(f"Failed to save CMDB Trigger log to database: {str(e)}")


async def process_cmdb_trigger_request(
    request_data: Dict[str, Any],
    request: Request,
    session: SessionDep,
    api_key: Optional[str] = None,
):
    """Process CMDB Trigger proxy request with API key verification and forwarding"""

    # Verify IP whitelist (empty list = deny all)
    verify_webhook_ip_whitelist(request, settings.webhook_ip_whitelist)

    # Verify CMDB Trigger webhook API key (skip if no API keys configured)
    verify_cmdb_trigger_webhook(request, api_key)

    # Get client IP from request
    client_ip = request.client.host
    if "x-forwarded-for" in request.headers:
        client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()
    elif "x-real-ip" in request.headers:
        client_ip = request.headers["x-real-ip"]

    # Extract request parameters
    target_host = request_data.get("host")
    method = request_data.get("method", "GET").upper()
    path = request_data.get("path", "/")
    query = request_data.get("query", "")
    headers = request_data.get("headers", {})
    body = request_data.get("body", {})
    author = request_data.get("author", "unknown")

    if not target_host:
        raise HTTPException(status_code=400, detail="Missing 'host' parameter")

    # Build target URL
    target_url = f"{target_host.rstrip('/')}{path}"
    if query:
        target_url += f"?{query}"

    # Initialize log entry
    log_entry = CmdbTriggerReqLogCreate(
        host=target_host,
        method=method,
        path=path,
        query=query,
        headers=headers,
        body=body,
        author=author,
        clientip=client_ip,  # This will be updated with actual response
        status=0,  # This will be updated with actual response
        output="",  # This will be updated with actual response
    )

    try:
        # Forward request to target server
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Prepare headers for forwarding
            forward_headers = {}
            if isinstance(headers, dict):
                for k, v in headers.items():
                    if k.lower() not in ["host", "content-length"]:
                        forward_headers[k] = str(v)

            # Make request based on method
            if method == "GET":
                response = await client.get(target_url, headers=forward_headers)
            elif method == "POST":
                if isinstance(body, dict) and body:
                    response = await client.post(
                        target_url, json=body, headers=forward_headers
                    )
                else:
                    response = await client.post(target_url, headers=forward_headers)
            elif method == "PUT":
                if isinstance(body, dict) and body:
                    response = await client.put(
                        target_url, json=body, headers=forward_headers
                    )
                else:
                    response = await client.put(target_url, headers=forward_headers)
            elif method == "DELETE":
                response = await client.delete(target_url, headers=forward_headers)
            elif method == "PATCH":
                if isinstance(body, dict) and body:
                    response = await client.patch(
                        target_url, json=body, headers=forward_headers
                    )
                else:
                    response = await client.patch(target_url, headers=forward_headers)
            else:
                raise HTTPException(
                    status_code=400, detail=f"Unsupported HTTP method: {method}"
                )

            # Get response data
            response_status = response.status_code
            response_text = response.text

            # Update log entry with actual response data
            log_entry.status = response_status
            log_entry.output = response_text
            # Keep the original client_ip from the request to this proxy

            # Save log to database
            log_cmdb_trigger_request(session, log_entry)

            # Return response similar to original request structure
            return {
                "status": response_status,
                "output": response_text,
                "clientip": client_ip,
                "processed_at": int(time.time()),
            }

    except httpx.TimeoutException:
        # Handle timeout
        error_msg = "Request to target server timed out"
        log_entry.status = 504
        log_entry.output = error_msg

        # Save error log
        log_cmdb_trigger_request(session, log_entry)

        raise HTTPException(status_code=504, detail=error_msg)

    except httpx.RequestError as e:
        # Handle connection errors
        error_msg = f"Failed to connect to target server: {str(e)}"
        log_entry.status = 502
        log_entry.output = error_msg

        # Save error log
        log_cmdb_trigger_request(session, log_entry)

        raise HTTPException(status_code=502, detail=error_msg)

    except Exception as e:
        # Handle other errors
        error_msg = f"Internal server error: {str(e)}"
        log_entry.status = 500
        log_entry.output = error_msg

        # Save error log
        log_cmdb_trigger_request(session, log_entry)

        raise HTTPException(status_code=500, detail=error_msg)
