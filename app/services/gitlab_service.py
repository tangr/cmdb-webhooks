from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from app.models.gitlab_reqlog import GitlabReqLog, GitlabReqLogCreate
from app.dependencies import SessionDep
from config.config import settings
from app.utils.webhook_security import (
    verify_gitlab_webhook,
    verify_webhook_ip_whitelist,
)
from typing import Dict, Any, Optional, List
import httpx
import json
import fnmatch
import yaml
from pathlib import Path
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Global mapping storage
_gitlab_jenkins_mapping: Dict[str, Any] = {}


def _find_project_root() -> Path:
    """Find the project root directory by looking for requirements.txt"""
    current_path = Path(__file__).resolve()
    for parent in current_path.parents:
        if (parent / "requirements.txt").exists():
            return parent
    return current_path.parent.parent.parent


def load_gitlab_jenkins_mapping() -> Dict[str, Any]:
    """Load GitLab to Jenkins mapping from YAML file"""
    project_root = _find_project_root()
    config_path = project_root / "config" / "gitlab_jenkins_mapping.yaml"

    try:
        with open(config_path, "r", encoding="utf-8") as file:
            config = yaml.safe_load(file)
            return config or {}
    except FileNotFoundError:
        logger.warning(f"GitLab-Jenkins mapping file not found at {config_path}")
        return {}
    except yaml.YAMLError as e:
        logger.error(f"Error parsing GitLab-Jenkins mapping YAML: {e}")
        return {}


def init_gitlab_jenkins_mapping():
    """Initialize GitLab-Jenkins mapping on startup"""
    global _gitlab_jenkins_mapping
    _gitlab_jenkins_mapping = load_gitlab_jenkins_mapping()
    mappings_count = len(_gitlab_jenkins_mapping.get("mappings", {}))
    logger.info(f"Loaded {mappings_count} GitLab-Jenkins mappings")


def get_jenkins_config(project_path: str) -> Optional[Dict[str, Any]]:
    """
    Get Jenkins configuration for a GitLab project path.
    Supports exact match and wildcard patterns.

    Args:
        project_path: GitLab project path (e.g., "group/project-name")

    Returns:
        Jenkins configuration dict or None if no match
    """
    mappings = _gitlab_jenkins_mapping.get("mappings", {})

    # Try exact match first
    if project_path in mappings:
        return mappings[project_path]

    # Try wildcard patterns
    for pattern, config in mappings.items():
        if fnmatch.fnmatch(project_path, pattern):
            return config

    # Use default configuration if enabled
    default_config = _gitlab_jenkins_mapping.get("default", {})
    if default_config.get("enabled", False):
        return default_config

    return None


def extract_field_value(payload: Dict[str, Any], field_path: str) -> Any:
    """
    Extract a value from payload using dot notation path.

    Args:
        payload: Source payload dict
        field_path: Dot notation path (e.g., "project.name", "commits[0].message")

    Returns:
        Extracted value or None if not found
    """
    try:
        current = payload
        parts = field_path.replace("[", ".").replace("]", "").split(".")

        for part in parts:
            if not part:
                continue
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list) and part.isdigit():
                index = int(part)
                current = current[index] if index < len(current) else None
            else:
                return None

            if current is None:
                return None

        return current
    except Exception as e:
        logger.debug(f"Failed to extract field '{field_path}': {e}")
        return None


def extract_fields(
    payload: Dict[str, Any], field_mapping: Dict[str, str]
) -> Dict[str, Any]:
    """
    Extract fields from payload according to field mapping configuration.

    Args:
        payload: Source GitLab payload
        field_mapping: Dict mapping output field names to source paths

    Returns:
        Dict with extracted fields
    """
    result = {}
    for output_field, source_path in field_mapping.items():
        value = extract_field_value(payload, source_path)
        if value is not None:
            result[output_field] = value
    return result


def get_branch_from_ref(ref: str) -> str:
    """Extract branch name from ref string (refs/heads/main -> main)"""
    if ref and ref.startswith("refs/heads/"):
        return ref[len("refs/heads/") :]
    if ref and ref.startswith("refs/tags/"):
        return ref[len("refs/tags/") :]
    return ref or ""


def log_gitlab_request(session: SessionDep, log_entry: GitlabReqLogCreate):
    """Log GitLab request to database based on configuration"""

    # Console logging
    if settings.enable_console_logging:
        log_message = (
            f"GitLab Webhook - "
            f"Event: {log_entry.event_type}, "
            f"Project: {log_entry.project_path}, "
            f"Status: {log_entry.status}, "
            f"Jenkins Job: {log_entry.jenkins_job or 'N/A'}"
        )

        if log_entry.error_message:
            log_message += f", Error: {log_entry.error_message}"
            logger.error(log_message)
        else:
            logger.info(log_message)

    # Database logging
    if settings.enable_database_logging:
        try:
            db_log = GitlabReqLog(**log_entry.model_dump())
            session.add(db_log)
            session.commit()
        except Exception as e:
            if settings.enable_console_logging:
                logger.error(f"Failed to save GitLab log to database: {str(e)}")


async def send_to_jenkins(
    jenkins_base_url: str,
    jenkins_job: str,
    jenkins_token: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Send payload to Jenkins Generic Webhook Trigger.

    Args:
        jenkins_base_url: Jenkins base URL
        jenkins_job: Jenkins job name (unused in generic trigger, kept for logging)
        jenkins_token: Jenkins trigger token
        payload: Payload to send

    Returns:
        Dict with status and response data
    """
    # Build Jenkins Generic Webhook Trigger URL
    jenkins_url = f"{jenkins_base_url.rstrip('/')}/generic-webhook-trigger/invoke"
    if jenkins_token:
        jenkins_url += f"?token={jenkins_token}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            jenkins_url,
            json=payload,
            headers={"Content-Type": "application/json"},
        )

        try:
            response_body = response.json()
        except Exception:
            response_body = {"raw": response.text}

        return {
            "status_code": response.status_code,
            "body": response_body,
        }


async def process_gitlab_webhook(
    request: Request,
    session: SessionDep,
    gitlab_token: Optional[str] = None,
    gitlab_event: Optional[str] = None,
):
    """
    Process GitLab System Hook webhook request.

    Args:
        request: FastAPI request object
        session: Database session
        gitlab_token: X-Gitlab-Token header value
        gitlab_event: X-Gitlab-Event header value

    Returns:
        JSON response with processing result
    """
    # Verify IP whitelist
    verify_webhook_ip_whitelist(request, settings.webhook_ip_whitelist)

    # Verify GitLab token
    verify_gitlab_webhook(request, gitlab_token)

    # Get client IP
    client_ip = request.client.host
    if "x-forwarded-for" in request.headers:
        client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()
    elif "x-real-ip" in request.headers:
        client_ip = request.headers["x-real-ip"]

    # Get request data
    method = request.method
    path = str(request.url.path)
    headers = dict(request.headers)

    # Read request body
    body_bytes = await request.body()
    try:
        body = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Determine event type from header or payload
    event_type = gitlab_event or body.get("object_kind", "unknown")
    event_type = event_type.lower().replace(" ", "_")

    # Get project path from payload
    project_path = ""
    if "project" in body:
        project_path = body["project"].get("path_with_namespace", "")
    elif "path_with_namespace" in body:
        project_path = body["path_with_namespace"]

    # Initialize log entry
    log_entry = GitlabReqLogCreate(
        event_type=event_type,
        project_path=project_path,
        method=method,
        path=path,
        headers=headers,
        body=body,
        clientip=client_ip,
        status=0,
        jenkins_job=None,
        jenkins_response=None,
        error_message=None,
    )

    # Check if event type is enabled
    event_enabled = False
    if event_type == "push" and settings.gitlab_enable_push_events:
        event_enabled = True
    elif event_type == "tag_push" and settings.gitlab_enable_tag_push_events:
        event_enabled = True
    elif event_type == "merge_request" and settings.gitlab_enable_merge_request_events:
        event_enabled = True

    if not event_enabled:
        log_entry.status = 200
        log_entry.error_message = f"Event type '{event_type}' is not enabled"
        log_gitlab_request(session, log_entry)
        return JSONResponse(
            content={
                "status": "skipped",
                "message": f"Event type '{event_type}' is not enabled",
            },
            status_code=200,
        )

    # Get Jenkins configuration for this project
    jenkins_config = get_jenkins_config(project_path)
    if not jenkins_config:
        log_entry.status = 200
        log_entry.error_message = (
            f"No Jenkins mapping found for project: {project_path}"
        )
        log_gitlab_request(session, log_entry)
        return JSONResponse(
            content={
                "status": "skipped",
                "message": f"No Jenkins mapping configured for project: {project_path}",
            },
            status_code=200,
        )

    # Check Jenkins base URL configuration
    jenkins_base_url = settings.gitlab_jenkins_base_url
    if not jenkins_base_url:
        log_entry.status = 500
        log_entry.error_message = "Jenkins base URL not configured"
        log_gitlab_request(session, log_entry)
        raise HTTPException(
            status_code=500, detail="Jenkins base URL not configured in settings"
        )

    # Get Jenkins job and token
    jenkins_job = jenkins_config.get("jenkins_job", "")
    jenkins_token = jenkins_config.get(
        "jenkins_token", settings.gitlab_jenkins_default_token
    )
    log_entry.jenkins_job = jenkins_job

    # Extract fields according to mapping
    field_mapping = jenkins_config.get("field_mapping", {})
    extracted_payload = extract_fields(body, field_mapping)

    # Add extra params if configured
    extra_params = jenkins_config.get("extra_params", {})
    extracted_payload.update(extra_params)

    # Add branch name (extracted from ref)
    if "ref" in extracted_payload:
        extracted_payload["branch"] = get_branch_from_ref(extracted_payload["ref"])

    try:
        # Send to Jenkins
        jenkins_result = await send_to_jenkins(
            jenkins_base_url,
            jenkins_job,
            jenkins_token,
            extracted_payload,
        )

        log_entry.status = jenkins_result["status_code"]
        log_entry.jenkins_response = jenkins_result["body"]

        # Log request
        log_gitlab_request(session, log_entry)

        return JSONResponse(
            content={
                "status": "success",
                "jenkins_status": jenkins_result["status_code"],
                "jenkins_response": jenkins_result["body"],
                "project_path": project_path,
                "event_type": event_type,
            },
            status_code=200,
        )

    except httpx.TimeoutException:
        error_msg = "Request to Jenkins timed out"
        log_entry.status = 504
        log_entry.error_message = error_msg
        log_gitlab_request(session, log_entry)
        raise HTTPException(status_code=504, detail=error_msg)

    except httpx.RequestError as e:
        error_msg = f"Failed to connect to Jenkins: {str(e)}"
        log_entry.status = 502
        log_entry.error_message = error_msg
        log_gitlab_request(session, log_entry)
        raise HTTPException(status_code=502, detail=error_msg)

    except Exception as e:
        error_msg = f"Internal server error: {str(e)}"
        log_entry.status = 500
        log_entry.error_message = error_msg
        log_gitlab_request(session, log_entry)
        raise HTTPException(status_code=500, detail=error_msg)
