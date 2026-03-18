from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from sqlmodel import select
from app.models.amis_jenkins_reqlog import AmisJenkinsReqLog, AmisJenkinsReqLogCreate
from app.models.pending_jenkins_job import (
    PendingJenkinsJob,
    PendingJenkinsJobCreate,
    PendingJenkinsJobRead,
)
from app.models.feishu_approval_reqlog import FeishuApprovalReqLog
from app.dependencies import SessionDep, User
from app.services.feishu_approval_service import FeishuApprovalService
from config.config import settings
from typing import Dict, Any, Optional, List
import httpx
import json
import base64
import yaml
import hashlib
import time
from pathlib import Path
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Global mapping storage
_amis_jenkins_mapping: Dict[str, Any] = {}
_amis_jenkins_config_version: str = ""


def _find_project_root() -> Path:
    """Find the project root directory by looking for requirements.txt"""
    current_path = Path(__file__).resolve()
    for parent in current_path.parents:
        if (parent / "requirements.txt").exists():
            return parent
    return current_path.parent.parent.parent


def _get_config_path() -> Path:
    """Get the path to amis_jenkins_mapping.yaml"""
    project_root = _find_project_root()
    return project_root / "config" / "amis_jenkins_mapping.yaml"


def _calculate_config_version(config_path: Path) -> str:
    """
    Calculate config version based on file content hash.

    Args:
        config_path: Path to the config file

    Returns:
        Short hash string (first 8 chars of md5)
    """
    try:
        with open(config_path, "rb") as file:
            content = file.read()
            return hashlib.md5(content).hexdigest()[:8]
    except Exception:
        return "unknown"


def load_amis_jenkins_mapping() -> Dict[str, Any]:
    """Load Amis Jenkins mapping from YAML file"""
    config_path = _get_config_path()

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
    global _amis_jenkins_mapping, _amis_jenkins_config_version
    _amis_jenkins_mapping = load_amis_jenkins_mapping()
    _amis_jenkins_config_version = _calculate_config_version(_get_config_path())
    forms = _amis_jenkins_mapping.get("forms") or {}
    logger.info(
        f"Loaded {len(forms)} Amis-Jenkins form mappings (version: {_amis_jenkins_config_version})"
    )


def get_config_version() -> str:
    """Get current config version"""
    return _amis_jenkins_config_version


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


def get_user_feishu_mapping() -> Dict[str, str]:
    """Get user to Feishu ID mapping from YAML configuration"""
    return _amis_jenkins_mapping.get("user_feishu_mapping") or {}


def get_user_feishu_id(username: str) -> str:
    """
    Get Feishu user ID for a given username.

    If user is configured in user_feishu_mapping, return the mapped ID.
    Otherwise, return the username as the default Feishu user ID.

    Args:
        username: System username

    Returns:
        Feishu user ID (mapped value or username as fallback)
    """
    mapping = get_user_feishu_mapping()
    return mapping.get(username, username)


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


def get_approval_config(form_id: str) -> Optional[Dict[str, Any]]:
    """
    Get approval configuration for a form.

    Args:
        form_id: Form identifier

    Returns:
        Approval config dict or None if not configured
    """
    form_config = get_form_config(form_id)
    if not form_config:
        return None
    return form_config.get("approval")


def is_approval_enabled(form_id: str) -> bool:
    """
    Check if approval is enabled for a form.

    Args:
        form_id: Form identifier

    Returns:
        True if approval is enabled, False otherwise
    """
    approval_config = get_approval_config(form_id)
    if not approval_config:
        return False
    return approval_config.get("enabled", False)


def get_all_forms() -> List[Dict[str, Any]]:
    """
    Get all form configurations with their IDs.

    Returns:
        List of form configs with form_id added
    """
    forms = _amis_jenkins_mapping.get("forms") or {}
    result = []
    for form_id, config in forms.items():
        approval_config = config.get("approval") or {}
        form_info = {
            "form_id": form_id,
            "title": config.get("title", form_id),
            "description": config.get("description", ""),
            "jenkins_job": config.get("jenkins_job", ""),
            "trigger_type": config.get("trigger_type", "generic_webhook"),
            "approval_enabled": approval_config.get("enabled", False),
        }
        result.append(form_info)
    return result


def _extract_all_form_fields_from_amis(
    schema: Dict[str, Any],
    modifiable_fields: List[str],
) -> List[Dict[str, Any]]:
    """
    Extract all form field definitions from Amis schema.
    Non-modifiable fields are marked as static (readonly display).

    Args:
        schema: Amis schema dict
        modifiable_fields: List of field names that can be modified

    Returns:
        List of Amis field definitions with non-modifiable fields set to static
    """
    import copy

    modifiable_set = set(modifiable_fields)
    found_fields = []
    found_names = set()

    def extract_from_node(node: Any) -> None:
        """Recursively search for fields and extract their complete definition."""
        if not isinstance(node, dict):
            return

        # Check if this node has a "name" attribute (is a form field)
        node_name = node.get("name", "")
        node_type = node.get("type", "")

        # Skip hidden fields and non-form-field types
        if node_type == "hidden" or not node_name or node_name.startswith("_"):
            pass
        elif node_name and node_name not in found_names:
            # Deep copy the entire field definition
            field_def = copy.deepcopy(node)

            # Remove any api/source that fetches dynamic data - use static options only
            if "source" in field_def:
                del field_def["source"]
            if "initFetchOn" in field_def:
                del field_def["initFetchOn"]

            # If not modifiable, set to static mode (readonly display)
            if node_name not in modifiable_set:
                field_def["static"] = True

            found_fields.append(field_def)
            found_names.add(node_name)

        # Recursively search in all dict/list values
        for key, value in node.items():
            if isinstance(value, dict):
                extract_from_node(value)
            elif isinstance(value, list):
                for item in value:
                    extract_from_node(item)

    extract_from_node(schema)
    return found_fields


def get_modifiable_fields_config(form_id: str) -> Dict[str, Any]:
    """
    Get modifiable fields configuration for a form.

    Args:
        form_id: Form identifier

    Returns:
        Dict with modifiable_fields list and Amis schema for all fields
        (non-modifiable fields are marked as static)
    """
    approval_config = get_approval_config(form_id)
    if not approval_config:
        return {"modifiable_fields": [], "schema": [], "max_executions": 0, "expire_hours": 0}

    modifiable_fields = approval_config.get("modifiable_fields", [])
    max_executions = approval_config.get("max_executions", 0)
    expire_hours = approval_config.get("expire_hours", 0)

    # Get form schema and extract all field definitions
    # Non-modifiable fields are marked as static (readonly)
    form_config = get_form_config(form_id)
    form_schema = form_config.get("schema", {}) if form_config else {}
    field_schema = _extract_all_form_fields_from_amis(form_schema, modifiable_fields)

    return {
        "modifiable_fields": modifiable_fields,
        "schema": field_schema,
        "max_executions": max_executions,
        "expire_hours": expire_hours,
    }


def _inject_version_field(schema: Dict[str, Any], version: str) -> Dict[str, Any]:
    """
    Inject a hidden version field into Amis form schema.

    Args:
        schema: Amis schema dict
        version: Config version string

    Returns:
        Modified schema with version field injected
    """
    import copy

    schema = copy.deepcopy(schema)
    version_field = {
        "type": "hidden",
        "name": "_schema_version",
        "value": version,
    }

    # Find the form body and inject the hidden field
    def inject_into_form(node: Dict[str, Any]) -> bool:
        """Recursively find form and inject version field. Returns True if injected."""
        if not isinstance(node, dict):
            return False

        # If this is a form, inject into its body
        if node.get("type") == "form":
            body = node.get("body", [])
            if isinstance(body, list):
                # Prepend version field to body
                node["body"] = [version_field] + body
            elif isinstance(body, dict):
                # Body is a single component, wrap in list
                node["body"] = [version_field, body]
            else:
                node["body"] = [version_field]
            return True

        # Search in body/items/controls for nested form
        for key in ["body", "items", "controls", "content"]:
            child = node.get(key)
            if isinstance(child, list):
                for item in child:
                    if inject_into_form(item):
                        return True
            elif isinstance(child, dict):
                if inject_into_form(child):
                    return True

        return False

    inject_into_form(schema)
    return schema


def get_form_schema(form_id: str) -> Optional[Dict[str, Any]]:
    """
    Get Amis schema for a form with version field injected.

    Args:
        form_id: Form identifier

    Returns:
        Amis schema dict with _schema_version hidden field, or None if not found
    """
    form_config = get_form_config(form_id)
    if not form_config:
        return None

    schema = form_config.get("schema")
    if not schema:
        return None

    # Inject version field into schema
    version = get_config_version()
    return _inject_version_field(schema, version)


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

    # Validate schema version to detect stale form submissions
    submitted_version = body.pop("_schema_version", None)
    current_version = get_config_version()
    logger.debug(
        f"Schema version check - submitted: {submitted_version}, current: {current_version}"
    )
    if submitted_version and submitted_version != current_version:
        return JSONResponse(
            content={
                "status": 1,
                "msg": "Form configuration has been updated. Please refresh the page to get the latest form.",
                "data": {
                    "error_type": "VERSION_MISMATCH",
                    "submitted_version": submitted_version,
                    "current_version": current_version,
                },
            },
            status_code=409,  # Conflict
        )

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

    # Add current user's username to payload for Jenkins
    body["submitted_by"] = current_user.username

    # Check if approval is enabled for this form
    if is_approval_enabled(form_id):
        return await _process_form_submit_with_approval(
            session=session,
            form_id=form_id,
            form_config=form_config,
            form_title=form_title,
            trigger_type=trigger_type,
            jenkins_job=jenkins_job,
            body=body,
            client_ip=client_ip,
            current_user=current_user,
        )

    # Direct Jenkins trigger (no approval required)
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


async def _process_form_submit_with_approval(
    session: SessionDep,
    form_id: str,
    form_config: Dict[str, Any],
    form_title: str,
    trigger_type: str,
    jenkins_job: str,
    body: Dict[str, Any],
    client_ip: str,
    current_user: User,
) -> JSONResponse:
    """
    Process form submission with Feishu approval.

    Creates an approval request and pending job record instead of triggering Jenkins directly.

    Args:
        session: Database session
        form_id: Form identifier
        form_config: Form configuration dict
        form_title: Form display title
        trigger_type: Jenkins trigger type
        jenkins_job: Jenkins job path
        body: Form data submitted by user
        client_ip: Client IP address
        current_user: Authenticated user

    Returns:
        JSON response with approval creation result
    """
    approval_config = get_approval_config(form_id)
    feishu_app = approval_config.get("feishu_app", "default")
    approval_code = approval_config.get("approval_code")  # Optional override

    # Get Feishu user ID for current user (falls back to username if not mapped)
    feishu_user_id = get_user_feishu_id(current_user.username)

    # Build form data for Feishu approval
    # If form_data_template is configured, use it; otherwise use default placeholders
    form_data_template = approval_config.get("form_data_template")

    # Prepare placeholder values
    request_params_json = json.dumps(body, ensure_ascii=False, indent=2)
    placeholders = {
        "form_id": form_id,
        "form_title": form_title,
        "jenkins_job": jenkins_job,
        "username": current_user.username,
        "request_params_json": request_params_json,
    }
    # Add all form field values as placeholders
    for field_name, field_value in body.items():
        if isinstance(field_value, (dict, list)):
            placeholders[field_name] = json.dumps(field_value, ensure_ascii=False)
        else:
            placeholders[field_name] = str(field_value) if field_value is not None else ""

    if form_data_template:
        # Use configured template
        feishu_form_data = {}
        for widget_id, template_value in form_data_template.items():
            try:
                # Replace placeholders in template
                value = template_value.format(**placeholders)
                feishu_form_data[widget_id] = value
            except KeyError as e:
                logger.warning(f"Unknown placeholder in form_data_template: {e}")
                feishu_form_data[widget_id] = template_value
    else:
        # No template configured - return error to prompt user to configure
        return JSONResponse(
            content={
                "status": 1,
                "msg": "Feishu approval form_data_template not configured. Please configure approval.form_data_template in amis_jenkins_mapping.yaml with your Feishu approval widget IDs.",
                "data": {
                    "error_type": "FORM_DATA_TEMPLATE_REQUIRED",
                    "hint": "Example: form_data_template: {\"widget-id1\": \"Job: {jenkins_job}\", \"widget-id2\": \"{request_params_json}\"}",
                },
            },
            status_code=400,
        )

    # Get multi-execution configuration
    modifiable_config = get_modifiable_fields_config(form_id)
    modifiable_fields = modifiable_config.get("modifiable_fields", [])
    field_schema = modifiable_config.get("schema", [])
    max_executions = modifiable_config.get("max_executions", 0)
    expire_hours = modifiable_config.get("expire_hours", 0)

    # Calculate expire_at timestamp
    expire_at = 0
    if expire_hours > 0:
        expire_at = int(time.time()) + (expire_hours * 3600)

    # Build modifiable_fields_options snapshot
    # This stores the list of modifiable fields and their complete Amis schema
    modifiable_fields_options = {
        "fields": modifiable_fields,
        "schema": field_schema,
    }

    try:
        # Create Feishu approval
        approval_result = await FeishuApprovalService.create_approval(
            session=session,
            app_name=feishu_app,
            feishu_user_id=feishu_user_id,
            form_data=feishu_form_data,
            username=current_user.username,
            clientip=client_ip,
            approval_code=approval_code,
        )

        # Create pending job record with multi-execution settings
        pending_job = PendingJenkinsJob(
            form_id=form_id,
            form_title=form_title,
            trigger_type=trigger_type,
            jenkins_job=jenkins_job,
            request_params=body,
            username=current_user.username,
            clientip=client_ip,
            approval_log_id=approval_result["log_id"],
            status="pending_approval",
            modifiable_fields_options=modifiable_fields_options,
            execution_count=0,
            max_executions=max_executions,
            expire_at=expire_at,
        )
        session.add(pending_job)
        session.commit()
        session.refresh(pending_job)

        logger.info(
            f"Created pending job {pending_job.id} with approval {approval_result['feishu_instance_code']}"
        )

        return JSONResponse(
            content={
                "status": 0,
                "msg": "Approval request created. Please wait for approval before execution.",
                "data": {},
                "debug": {
                    "pending_job_id": pending_job.id,
                    "approval_log_id": approval_result["log_id"],
                    "feishu_instance_code": approval_result["feishu_instance_code"],
                    "approval_status": "pending",
                },
            },
            status_code=200,
        )

    except ValueError as e:
        logger.error(f"Approval creation failed: {e}")
        return JSONResponse(
            content={
                "status": 1,
                "msg": f"Failed to create approval: {str(e)}",
                "data": {"error_type": "APPROVAL_CONFIG_ERROR"},
            },
            status_code=400,
        )

    except Exception as e:
        logger.error(f"Approval creation failed: {e}")
        return JSONResponse(
            content={
                "status": 1,
                "msg": f"Failed to create approval: {str(e)}",
                "data": {"error_type": "APPROVAL_ERROR"},
            },
            status_code=500,
        )


def get_pending_jobs(
    session: SessionDep,
    username: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """
    Get pending Jenkins jobs with optional filters.

    Args:
        session: Database session
        username: Filter by username (None for all users)
        status: Filter by status (None for all statuses)
        limit: Max records to return
        offset: Offset for pagination

    Returns:
        List of pending job records with approval info
    """
    statement = select(PendingJenkinsJob)

    if username:
        statement = statement.where(PendingJenkinsJob.username == username)
    if status:
        statement = statement.where(PendingJenkinsJob.status == status)

    statement = statement.order_by(PendingJenkinsJob.created_at.desc())
    statement = statement.offset(offset).limit(limit)

    jobs = session.exec(statement).all()

    result = []
    for job in jobs:
        job_dict = PendingJenkinsJobRead.model_validate(job).model_dump()
        # Add approval info
        approval_log = session.get(FeishuApprovalReqLog, job.approval_log_id)
        if approval_log:
            job_dict["approval_status"] = approval_log.status
            job_dict["feishu_instance_code"] = approval_log.feishu_instance_code
        result.append(job_dict)

    return result


async def sync_pending_job_status(session: SessionDep, job_id: int) -> Dict[str, Any]:
    """
    Sync pending job status from Feishu approval.

    Args:
        session: Database session
        job_id: Pending job ID

    Returns:
        Dict with updated status info
    """
    job = session.get(PendingJenkinsJob, job_id)
    if not job:
        raise ValueError(f"Pending job not found: {job_id}")

    # Get approval status from Feishu
    approval_status = await FeishuApprovalService.get_approval_status(
        session=session, log_id=job.approval_log_id
    )

    # Map Feishu status to job status
    feishu_status = approval_status.get("status", "pending")
    status_mapping = {
        "pending": "pending_approval",
        "approved": "approved",
        "rejected": "rejected",
        "canceled": "canceled",
    }
    new_job_status = status_mapping.get(feishu_status, job.status)

    # Update job status if changed
    if new_job_status != job.status:
        job.status = new_job_status
        job.updated_at = int(time.time())
        session.add(job)
        session.commit()

    return {
        "job_id": job_id,
        "job_status": job.status,
        "approval_status": feishu_status,
        "feishu_instance_code": approval_status.get("feishu_instance_code"),
    }


async def execute_pending_job(
    session: SessionDep,
    job_id: int,
    modified_fields: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Execute a pending Jenkins job after approval.

    Supports multi-execution: if max_executions > 0 or expire_at > 0,
    the job can be executed multiple times until limits are reached.

    Args:
        session: Database session
        job_id: Pending job ID
        modified_fields: Optional dict of field values to override (must be in modifiable_fields list)

    Returns:
        Dict with execution result
    """
    job = session.get(PendingJenkinsJob, job_id)
    if not job:
        raise ValueError(f"Pending job not found: {job_id}")

    # Sync status first to ensure we have latest approval status
    await sync_pending_job_status(session, job_id)
    session.refresh(job)

    # Check job status - allow approved, also allow re-execution if not exhausted/expired
    if job.status == "exhausted":
        raise ValueError("Job has reached maximum execution count")
    if job.status == "expired":
        raise ValueError("Job has expired")
    if job.status not in ["approved"]:
        raise ValueError(f"Job is not approved. Current status: {job.status}")

    # Check expiration
    current_time = int(time.time())
    if job.expire_at > 0 and current_time > job.expire_at:
        job.status = "expired"
        job.updated_at = current_time
        session.add(job)
        session.commit()
        raise ValueError("Job has expired")

    # Check execution count limit
    if job.max_executions > 0 and job.execution_count >= job.max_executions:
        job.status = "exhausted"
        job.updated_at = current_time
        session.add(job)
        session.commit()
        raise ValueError("Job has reached maximum execution count")

    # Get form config for Jenkins connection settings
    form_config = get_form_config(job.form_id)
    if not form_config:
        raise ValueError(f"Form config not found: {job.form_id}")

    jenkins_base_url = form_config.get("jenkins_base_url") or get_jenkins_base_url()
    if not jenkins_base_url:
        raise ValueError("Jenkins base URL not configured")

    # Build execution params - start with original request_params
    execution_params = dict(job.request_params)

    # Apply modified fields if provided
    if modified_fields:
        # Validate modified fields are allowed
        modifiable_config = job.modifiable_fields_options or {}
        allowed_fields = modifiable_config.get("fields", [])
        field_schema_list = modifiable_config.get("schema", [])

        # Build a lookup dict from field name to its schema
        field_schema_map = {f.get("name"): f for f in field_schema_list if f.get("name")}

        for field_name, field_value in modified_fields.items():
            if field_name not in allowed_fields:
                raise ValueError(f"Field '{field_name}' is not modifiable for this job")

            # Validate value is in allowed options (if field has options)
            field_def = field_schema_map.get(field_name, {})
            field_options = field_def.get("options", [])

            if field_options:
                # Extract allowed values from options
                allowed_values = []
                for opt in field_options:
                    if isinstance(opt, dict):
                        allowed_values.append(opt.get("value"))
                    else:
                        allowed_values.append(opt)

                # Handle multi-select (list of values)
                if isinstance(field_value, list):
                    for val in field_value:
                        if val not in allowed_values:
                            raise ValueError(
                                f"Invalid value '{val}' for field '{field_name}'. "
                                f"Allowed values: {allowed_values}"
                            )
                else:
                    if field_value not in allowed_values:
                        raise ValueError(
                            f"Invalid value '{field_value}' for field '{field_name}'. "
                            f"Allowed values: {allowed_values}"
                        )

            execution_params[field_name] = field_value

    try:
        if job.trigger_type == "generic_webhook":
            jenkins_token = (
                form_config.get("jenkins_token") or get_jenkins_default_token()
            )
            jenkins_result = await send_to_jenkins_generic_webhook(
                jenkins_base_url,
                jenkins_token,
                execution_params,
            )
        elif job.trigger_type == "remote_api":
            jenkins_user = form_config.get("jenkins_user") or get_jenkins_default_user()
            jenkins_api_token = (
                form_config.get("jenkins_api_token") or get_jenkins_default_api_token()
            )
            if not jenkins_user or not jenkins_api_token:
                raise ValueError("Jenkins user or API token not configured for Remote API")

            jenkins_result = await send_to_jenkins_remote_api(
                jenkins_base_url,
                job.jenkins_job,
                jenkins_user,
                jenkins_api_token,
                execution_params,
            )
        else:
            raise ValueError(f"Unknown trigger type: {job.trigger_type}")

        # Update job with result
        is_success = jenkins_result["status_code"] in [200, 201, 202]
        current_time = int(time.time())

        if is_success:
            # Increment execution count
            job.execution_count += 1
            job.error_message = None

            # Determine new status based on limits
            if job.max_executions > 0 and job.execution_count >= job.max_executions:
                job.status = "exhausted"
            elif job.expire_at > 0 and current_time > job.expire_at:
                job.status = "expired"
            else:
                # Keep approved for multi-execution
                job.status = "approved"
        else:
            # Keep approved if failed, so user can retry
            job.status = "approved"
            job.error_message = f"Jenkins returned status {jenkins_result['status_code']}"

        job.jenkins_response = jenkins_result["body"]
        job.updated_at = current_time
        session.add(job)
        session.commit()

        # Also log to amis_jenkins_reqlog for consistency
        log_entry = AmisJenkinsReqLogCreate(
            form_id=job.form_id,
            form_title=job.form_title,
            trigger_type=job.trigger_type,
            jenkins_job=job.jenkins_job,
            request_params=execution_params,  # Log actual params used
            clientip=job.clientip,
            username=job.username,
            status=jenkins_result["status_code"],
            jenkins_response=jenkins_result["body"],
            error_message=None if is_success else job.error_message,
        )
        log_amis_jenkins_request(session, log_entry)

        return {
            "success": is_success,
            "job_id": job_id,
            "job_status": job.status,
            "execution_count": job.execution_count,
            "max_executions": job.max_executions,
            "expire_at": job.expire_at,
            "jenkins_status": jenkins_result["status_code"],
            "jenkins_response": jenkins_result["body"],
            "executed_params": execution_params,
        }

    except httpx.TimeoutException:
        job.error_message = "Request to Jenkins timed out"
        job.updated_at = int(time.time())
        session.add(job)
        session.commit()
        raise ValueError(job.error_message)

    except httpx.RequestError as e:
        job.error_message = f"Failed to connect to Jenkins: {str(e)}"
        job.updated_at = int(time.time())
        session.add(job)
        session.commit()
        raise ValueError(job.error_message)
