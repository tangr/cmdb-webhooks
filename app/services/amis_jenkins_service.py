from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from app.models.amis_jenkins_reqlog import AmisJenkinsReqLog, AmisJenkinsReqLogCreate
from app.dependencies import SessionDep, User
from config.config import settings
from typing import Dict, Any, Optional, List
import httpx
import json
import base64
import yaml
from pathlib import Path
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Global mapping storage
_amis_jenkins_mapping: Dict[str, Any] = {}


def _find_project_root() -> Path:
    """Find the project root directory by looking for requirements.txt"""
    current_path = Path(__file__).resolve()
    for parent in current_path.parents:
        if (parent / "requirements.txt").exists():
            return parent
    return current_path.parent.parent.parent


def load_amis_jenkins_mapping() -> Dict[str, Any]:
    """Load Amis Jenkins mapping from YAML file"""
    project_root = _find_project_root()
    config_path = project_root / "config" / "amis_jenkins_mapping.yaml"

    try:
        with open(config_path, "r", encoding="utf-8") as file:
            config = yaml.safe_load(file)
            return config or {}
    except FileNotFoundError:
        logger.warning(f"Amis-Jenkins mapping file not found at {config_path}")
        return {}
    except yaml.YAMLError as e:
        logger.error(f"Error parsing Amis-Jenkins mapping YAML: {e}")
        return {}


def init_amis_jenkins_mapping():
    """Initialize Amis-Jenkins mapping on startup"""
    global _amis_jenkins_mapping
    _amis_jenkins_mapping = load_amis_jenkins_mapping()
    forms = _amis_jenkins_mapping.get("forms") or {}
    logger.info(f"Loaded {len(forms)} Amis-Jenkins form mappings")


def get_jenkins_base_url() -> str:
    """Get Jenkins base URL from YAML configuration"""
    return _amis_jenkins_mapping.get("jenkins_base_url", "")


def get_jenkins_default_token() -> str:
    """Get Jenkins default token from YAML configuration"""
    return _amis_jenkins_mapping.get("jenkins_default_token", "")


def get_jenkins_default_user() -> str:
    """Get Jenkins default user from YAML configuration"""
    return _amis_jenkins_mapping.get("jenkins_default_user", "")


def get_jenkins_default_api_token() -> str:
    """Get Jenkins default API token from YAML configuration"""
    return _amis_jenkins_mapping.get("jenkins_default_api_token", "")


def get_form_config(form_id: str) -> Optional[Dict[str, Any]]:
    """
    Get form configuration by form ID.

    Args:
        form_id: Form identifier

    Returns:
        Form configuration dict or None if not found
    """
    forms = _amis_jenkins_mapping.get("forms") or {}
    return forms.get(form_id)


def get_all_forms() -> List[Dict[str, Any]]:
    """
    Get all form configurations with their IDs.

    Returns:
        List of form configs with form_id added
    """
    forms = _amis_jenkins_mapping.get("forms") or {}
    result = []
    for form_id, config in forms.items():
        form_info = {
            "form_id": form_id,
            "title": config.get("title", form_id),
            "description": config.get("description", ""),
            "jenkins_job": config.get("jenkins_job", ""),
            "trigger_type": config.get("trigger_type", "generic_webhook"),
        }
        result.append(form_info)
    return result


def get_form_schema(form_id: str) -> Optional[Dict[str, Any]]:
    """
    Get Amis schema for a form.

    Args:
        form_id: Form identifier

    Returns:
        Amis schema dict or None if not found
    """
    form_config = get_form_config(form_id)
    if not form_config:
        return None
    return form_config.get("schema")


def log_amis_jenkins_request(session: SessionDep, log_entry: AmisJenkinsReqLogCreate):
    """Log Amis Jenkins request to database based on configuration"""

    # Console logging
    if settings.enable_console_logging:
        log_message = (
            f"Amis Jenkins - "
            f"Form: {log_entry.form_id}, "
            f"User: {log_entry.username}, "
            f"Job: {log_entry.jenkins_job}, "
            f"Status: {log_entry.status}"
        )

        if log_entry.error_message:
            log_message += f", Error: {log_entry.error_message}"
            logger.error(log_message)
        else:
            logger.info(log_message)

    # Database logging
    if settings.enable_database_logging:
        try:
            db_log = AmisJenkinsReqLog(**log_entry.model_dump())
            session.add(db_log)
            session.commit()
        except Exception as e:
            if settings.enable_console_logging:
                logger.error(f"Failed to save Amis Jenkins log to database: {str(e)}")


async def send_to_jenkins_generic_webhook(
    jenkins_base_url: str,
    jenkins_token: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Send payload to Jenkins Generic Webhook Trigger.

    Args:
        jenkins_base_url: Jenkins base URL
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


async def send_to_jenkins_remote_api(
    jenkins_base_url: str,
    jenkins_job: str,
    jenkins_user: str,
    jenkins_api_token: str,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Send parameters to Jenkins Remote API (buildWithParameters).

    Args:
        jenkins_base_url: Jenkins base URL
        jenkins_job: Jenkins job path (e.g., "folder/job-name")
        jenkins_user: Jenkins username
        jenkins_api_token: Jenkins API token
        params: Parameters to send

    Returns:
        Dict with status and response data
    """
    # Build Jenkins buildWithParameters URL
    # Handle job path with folders (convert folder/job to job/folder/job/job-name)
    job_path = jenkins_job.replace("/", "/job/")
    jenkins_url = f"{jenkins_base_url.rstrip('/')}/job/{job_path}/buildWithParameters"

    # Create Basic Auth header
    auth_string = f"{jenkins_user}:{jenkins_api_token}"
    auth_bytes = base64.b64encode(auth_string.encode("utf-8")).decode("utf-8")

    headers = {
        "Authorization": f"Basic {auth_bytes}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    # Convert params to form data (flatten nested structures)
    form_data = {}
    for key, value in params.items():
        if isinstance(value, (dict, list)):
            form_data[key] = json.dumps(value)
        elif isinstance(value, bool):
            form_data[key] = str(value).lower()
        else:
            form_data[key] = str(value) if value is not None else ""

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            jenkins_url,
            data=form_data,
            headers=headers,
        )

        # Jenkins returns 201 for successful build trigger
        try:
            response_body = response.json()
        except Exception:
            response_body = {"raw": response.text}

        return {
            "status_code": response.status_code,
            "body": response_body,
        }


async def process_form_submit(
    request: Request,
    session: SessionDep,
    form_id: str,
    current_user: User,
) -> JSONResponse:
    """
    Process Amis form submission and forward to Jenkins.

    Args:
        request: FastAPI request object
        session: Database session
        form_id: Form identifier
        current_user: Authenticated user

    Returns:
        JSON response with processing result
    """
    # Get client IP
    client_ip = request.client.host
    if "x-forwarded-for" in request.headers:
        client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()
    elif "x-real-ip" in request.headers:
        client_ip = request.headers["x-real-ip"]

    # Get form configuration
    form_config = get_form_config(form_id)
    if not form_config:
        raise HTTPException(
            status_code=404,
            detail=f"Form not found: {form_id}",
        )

    # Read request body
    body_bytes = await request.body()
    try:
        body = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Extract form title and Jenkins config
    form_title = form_config.get("title", form_id)
    jenkins_job = form_config.get("jenkins_job", "")
    trigger_type = form_config.get("trigger_type", "generic_webhook")

    # Get Jenkins connection config (form config can override global config)
    jenkins_base_url = form_config.get("jenkins_base_url") or get_jenkins_base_url()

    # Initialize log entry
    log_entry = AmisJenkinsReqLogCreate(
        form_id=form_id,
        form_title=form_title,
        trigger_type=trigger_type,
        jenkins_job=jenkins_job,
        request_params=body,
        clientip=client_ip,
        username=current_user.username,
        status=0,
        jenkins_response=None,
        error_message=None,
    )

    # Check Jenkins base URL configuration
    if not jenkins_base_url:
        log_entry.status = 500
        log_entry.error_message = "Jenkins base URL not configured"
        log_amis_jenkins_request(session, log_entry)
        raise HTTPException(
            status_code=500,
            detail="Jenkins base URL not configured in amis_jenkins_mapping.yaml",
        )

    # Check Jenkins job configuration
    if not jenkins_job:
        log_entry.status = 500
        log_entry.error_message = "Jenkins job not configured for this form"
        log_amis_jenkins_request(session, log_entry)
        raise HTTPException(
            status_code=500,
            detail="Jenkins job not configured for this form",
        )

    try:
        if trigger_type == "generic_webhook":
            # Generic Webhook Trigger
            jenkins_token = (
                form_config.get("jenkins_token") or get_jenkins_default_token()
            )

            jenkins_result = await send_to_jenkins_generic_webhook(
                jenkins_base_url,
                jenkins_token,
                body,
            )
        elif trigger_type == "remote_api":
            # Remote API (buildWithParameters)
            jenkins_user = form_config.get("jenkins_user") or get_jenkins_default_user()
            jenkins_api_token = (
                form_config.get("jenkins_api_token") or get_jenkins_default_api_token()
            )

            if not jenkins_user or not jenkins_api_token:
                log_entry.status = 500
                log_entry.error_message = (
                    "Jenkins user or API token not configured for Remote API"
                )
                log_amis_jenkins_request(session, log_entry)
                raise HTTPException(
                    status_code=500,
                    detail="Jenkins user or API token not configured for Remote API trigger type",
                )

            jenkins_result = await send_to_jenkins_remote_api(
                jenkins_base_url,
                jenkins_job,
                jenkins_user,
                jenkins_api_token,
                body,
            )
        else:
            log_entry.status = 400
            log_entry.error_message = f"Unknown trigger type: {trigger_type}"
            log_amis_jenkins_request(session, log_entry)
            raise HTTPException(
                status_code=400,
                detail=f"Unknown trigger type: {trigger_type}. Use 'generic_webhook' or 'remote_api'",
            )

        log_entry.status = jenkins_result["status_code"]
        log_entry.jenkins_response = jenkins_result["body"]

        # Log request
        log_amis_jenkins_request(session, log_entry)

        # Return Amis-compatible response format
        # Amis expects {"status": 0, "msg": "success", "data": {...}} for success
        # IMPORTANT: Do NOT put extra fields in "data" as Amis will merge them
        # into form data, causing them to be sent in subsequent submissions
        is_success = jenkins_result["status_code"] in [200, 201, 202]
        return JSONResponse(
            content={
                "status": 0 if is_success else 1,
                "msg": (
                    "Jenkins build triggered successfully"
                    if is_success
                    else "Jenkins build trigger failed"
                ),
                "data": {},
                "debug": {
                    "jenkins_status": jenkins_result["status_code"],
                    "jenkins_response": jenkins_result["body"],
                    "form_id": form_id,
                    "trigger_type": trigger_type,
                },
            },
            status_code=200 if is_success else jenkins_result["status_code"],
        )

    except httpx.TimeoutException:
        error_msg = "Request to Jenkins timed out"
        log_entry.status = 504
        log_entry.error_message = error_msg
        log_amis_jenkins_request(session, log_entry)
        return JSONResponse(
            content={"status": 1, "msg": error_msg, "data": None},
            status_code=504,
        )

    except httpx.RequestError as e:
        error_msg = f"Failed to connect to Jenkins: {str(e)}"
        log_entry.status = 502
        log_entry.error_message = error_msg
        log_amis_jenkins_request(session, log_entry)
        return JSONResponse(
            content={"status": 1, "msg": error_msg, "data": None},
            status_code=502,
        )

    except HTTPException:
        raise

    except Exception as e:
        error_msg = f"Internal server error: {str(e)}"
        log_entry.status = 500
        log_entry.error_message = error_msg
        log_amis_jenkins_request(session, log_entry)
        return JSONResponse(
            content={"status": 1, "msg": error_msg, "data": None},
            status_code=500,
        )
