from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlmodel import select
from app.models.feishu_reqlog import FeishuReqLog, FeishuReqLogCreate
from app.dependencies import SessionDep
from typing import Dict, Any
import httpx
import json
import time

router = APIRouter()


@router.post("/webhook/{webhook_id}")
async def feishu_webhook_proxy(
    webhook_id: str,
    request: Request,
    session: SessionDep,
):
    """Feishu webhook proxy endpoint"""

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

    # Feishu API URL
    feishu_url = f"https://open.feishu.cn/open-apis/bot/v2/hook/{webhook_id}"

    # Initialize log entry
    log_entry = FeishuReqLogCreate(
        webhook_id=webhook_id,
        method=method,
        path=path,
        query=query,
        headers=headers,
        body=body,
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
                if k.lower() not in ["host", "x-forwarded-for", "x-real-ip"]
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


@router.get("/logs")
def get_feishu_logs(session: SessionDep, skip: int = 0, limit: int = 100):
    """Get Feishu webhook logs"""
    statement = (
        select(FeishuReqLog)
        .offset(skip)
        .limit(limit)
        .order_by(FeishuReqLog.created_at.desc())
    )
    logs = session.exec(statement).all()
    return logs


@router.get("/logs/{log_id}")
def get_feishu_log(log_id: int, session: SessionDep):
    """Get single Feishu webhook log by ID"""
    log = session.get(FeishuReqLog, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    return log
