import httpx
import json
from typing import Dict, Any, Tuple, List
from urllib.parse import parse_qs
from pathlib import Path
from fastapi import HTTPException
from sqlmodel import Session
import yaml

from app.models.vecmdb_trigger_reqlog import (
    VecmdbTriggerReqLog,
    VecmdbTriggerReqLogCreate,
)
from config.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Global vecmdb trigger configuration storage
_vecmdb_trigger_config: Dict[str, Any] = {}


def _find_project_root() -> Path:
    """Find the project root directory by looking for requirements.txt"""
    current_path = Path(__file__).resolve()
    for parent in current_path.parents:
        if (parent / "requirements.txt").exists():
            return parent
    return current_path.parent.parent.parent


def load_vecmdb_trigger_config() -> Dict[str, Any]:
    """Load veCMDB Trigger configuration from YAML file"""
    project_root = _find_project_root()
    config_path = project_root / "config" / "vecmdb_trigger_config.yaml"

    try:
        with open(config_path, "r", encoding="utf-8") as file:
            config = yaml.safe_load(file)
            return config or {}
    except FileNotFoundError:
        logger.warning(f"veCMDB Trigger config file not found at {config_path}")
        return {}
    except yaml.YAMLError as e:
        logger.error(f"Error parsing veCMDB Trigger config YAML: {e}")
        return {}


def init_vecmdb_trigger_config():
    """Initialize veCMDB Trigger configuration on startup"""
    global _vecmdb_trigger_config
    _vecmdb_trigger_config = load_vecmdb_trigger_config()
    api_keys = _vecmdb_trigger_config.get("vecmdb_trigger_webhook_api_keys") or []
    targets = _vecmdb_trigger_config.get("cmdb_trigger_targets") or {}
    prometheus_configs = _vecmdb_trigger_config.get("prometheus_sd_configs") or {}
    logger.info(
        f"Loaded veCMDB Trigger config: "
        f"api_keys={len(api_keys)} key(s), "
        f"cmdb_trigger_targets={len(targets)} target(s), "
        f"prometheus_sd_configs={len(prometheus_configs)} config(s)"
    )


def get_vecmdb_trigger_api_keys() -> List[str]:
    """Get the list of veCMDB Trigger API keys for webhook verification"""
    keys = _vecmdb_trigger_config.get("vecmdb_trigger_webhook_api_keys") or []
    if isinstance(keys, list):
        return [str(k).strip() for k in keys if str(k).strip()]
    return []


def get_default_headers() -> Dict[str, str]:
    """Get default HTTP headers for target API requests"""
    return dict(_vecmdb_trigger_config.get("default_headers") or {})


def get_cmdb_trigger_targets() -> Dict[str, Any]:
    """Get CMDB trigger target configurations"""
    return dict(_vecmdb_trigger_config.get("cmdb_trigger_targets") or {})


def get_prometheus_sd_configs() -> Dict[str, Any]:
    """Get Prometheus service discovery configurations"""
    return dict(_vecmdb_trigger_config.get("prometheus_sd_configs") or {})


def log_vecmdb_trigger_request(
    session: Session, log_entry: VecmdbTriggerReqLogCreate
):
    """Log veCMDB Trigger request to database based on configuration"""

    # Console logging
    if settings.enable_console_logging:
        log_message = (
            f"veCMDB Trigger - "
            f"Target: {log_entry.target_name}, "
            f"Request ID: {log_entry.request_id}, "
            f"Method: {log_entry.method}, "
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
            db_log = VecmdbTriggerReqLog(**log_entry.model_dump())
            session.add(db_log)
            session.commit()
        except Exception as e:
            if settings.enable_console_logging:
                logger.error(
                    f"Failed to save veCMDB Trigger log to database: {str(e)}"
                )


class VecmdbTriggerService:
    """Service for handling CMDB trigger proxy operations"""

    def get_target_config(self, target_name: str) -> Dict[str, Any]:
        """Get and validate target configuration"""
        targets = get_cmdb_trigger_targets()
        if target_name not in targets:
            available_targets = list(targets.keys())
            error_msg = f"Target '{target_name}' not found. Available targets: {available_targets}"
            logger.error(error_msg)
            raise HTTPException(status_code=404, detail=error_msg)

        return targets[target_name]

    def transform_request(
        self,
        cmdb_body: Dict[str, Any],
        client_ip: str,
        target_config: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Transform CMDB trigger request to separate request config and body"""

        # Get field mappings from target config
        field_mappings = target_config.get("field_mappings", {})
        nodes_mapping_uuid = field_mappings.get("nodes_mapping_uuid", {})
        nodes_mapping_name = field_mappings.get("nodes_mapping_name", {})
        platform_mapping = field_mappings.get("platform_mapping", {})
        default_fields = field_mappings.get("default_fields", {})

        # Start with a copy of the original body (transparent forwarding)
        body_data = dict(cmdb_body)

        # Apply platform transformation if mapping exists
        raw_platform = cmdb_body.get("platform")
        if raw_platform and platform_mapping:
            body_data["platform"] = platform_mapping.get(
                raw_platform, raw_platform
            )

        # Handle nodes field transformation
        raw_nodes = cmdb_body.get("nodes")
        if raw_nodes and isinstance(raw_nodes, str) and nodes_mapping_uuid:
            node_names = [name.strip() for name in raw_nodes.split(",")]
            transformed_nodes = []
            for node_name in node_names:
                # Find UUID for each node name (reverse lookup: name -> UUID)
                node_uuid = node_name
                for uuid, name in nodes_mapping_uuid.items():
                    if name == node_name:
                        node_uuid = uuid
                        break
                transformed_nodes.append(node_uuid)
            body_data["nodes"] = transformed_nodes

        # Handle nodes_display field transformation
        raw_nodes_display = cmdb_body.get("nodes_display")
        if raw_nodes_display and isinstance(raw_nodes_display, str) and nodes_mapping_name:
            node_display_names = [
                name.strip() for name in raw_nodes_display.split(",")
            ]
            body_data["nodes_display"] = [
                nodes_mapping_name.get(name, name)
                for name in node_display_names
            ]

        # Merge default fields from config (don't overwrite existing keys)
        for key, value in default_fields.items():
            if key not in body_data:
                body_data[key] = value

        # Remove None values
        body_data = {k: v for k, v in body_data.items() if v is not None}

        # Create headers by merging default headers with target-specific headers
        headers = get_default_headers()
        target_headers = target_config.get("target_api_headers", {})
        headers.update(target_headers)

        # Build request configuration
        request_config = {
            "host": target_config.get("target_api_base_url", ""),
            "method": target_config.get("target_api_method", "POST"),
            "path": target_config.get("target_api_path", ""),
            "query": target_config.get("target_api_query", ""),
            "headers": headers,
        }

        request_id = cmdb_body.get("id", "unknown")
        logger.info(f"Transformed CMDB request {request_id} for target")

        # Log field transformations
        if raw_nodes:
            logger.debug(
                f"Field transformations: nodes '{raw_nodes}' -> {body_data.get('nodes')}, "
                f"platform '{raw_platform}' -> '{body_data.get('platform')}'"
            )
        elif raw_nodes_display:
            logger.debug(
                f"Field transformations: nodes_display '{raw_nodes_display}' -> {body_data.get('nodes_display')}, "
                f"platform '{raw_platform}' -> '{body_data.get('platform')}'"
            )

        return request_config, body_data

    async def forward_request(
        self,
        request_config: Dict[str, Any],
        body_data: Dict[str, Any],
        target_config: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], int]:
        """Forward transformed request to target API"""

        # Build target URL using config values
        target_api_base_url = target_config.get("target_api_base_url")

        # Build API path with template variable support
        target_api_path = target_config.get("target_api_path", "")
        if target_api_path and "{{" in target_api_path:
            for key, value in body_data.items():
                if value is not None:
                    target_api_path = target_api_path.replace(
                        f"{{{{{key}}}}}", str(value)
                    )

        target_url = f"{target_api_base_url}{target_api_path}"
        timeout = target_config.get("target_api_timeout", 30)
        request_id = body_data.get("id", "unknown")

        try:
            logger.info(f"Forwarding request {request_id} to {target_url}")
            logger.debug(f"Request method: {request_config['method']}")
            logger.debug(f"Request path: {request_config['path']}")
            logger.debug(f"Request query: {request_config['query']}")
            logger.debug(f"Request headers: {request_config['headers']}")
            logger.debug(f"Request body: {body_data}")

            # Parse query string to dict for httpx
            query_params = None
            if request_config["query"]:
                parsed_query = parse_qs(request_config["query"])
                query_params = {
                    k: v[0] if v else "" for k, v in parsed_query.items()
                }

            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(
                    method=request_config["method"],
                    url=target_url,
                    params=query_params,
                    json=body_data,
                    headers=request_config["headers"],
                )

                logger.info(f"Target API response status: {response.status_code}")
                logger.debug(f"Target API response: {response.text}")

                try:
                    response_data = response.json()
                except Exception:
                    response_data = {"raw_response": response.text}

                logger.info(
                    f"Forwarded request {request_id} with status {response.status_code}"
                )
                return response_data, response.status_code

        except httpx.TimeoutException:
            error_msg = f"Timeout while forwarding request to {target_url}"
            logger.error(error_msg)
            raise HTTPException(status_code=504, detail=error_msg)

        except httpx.RequestError as e:
            error_msg = (
                f"Request error while forwarding to {target_url}: {str(e)}"
            )
            logger.error(error_msg)
            raise HTTPException(status_code=502, detail=error_msg)

    async def process_cmdb_request(
        self,
        cmdb_body: Dict[str, Any],
        client_ip: str,
        target_name: str,
        session: Session = None,
    ) -> Dict[str, Any]:
        """Main method to process CMDB trigger requests for specific target"""

        request_id = cmdb_body.get("id", "unknown")

        logger.info(
            f"Processing CMDB request {request_id} from {client_ip} for target '{target_name}'"
        )

        # Prepare log entry data
        log_data = {
            "target_name": target_name,
            "request_id": request_id,
            "method": "",
            "path": "",
            "headers": {},
            "body": {},
            "clientip": client_ip,
            "status": 0,
            "target_response": None,
            "error_message": None,
        }

        try:
            # Get and validate target configuration
            target_config = self.get_target_config(target_name)

            # Transform request using target-specific configuration
            request_config, body_data = self.transform_request(
                cmdb_body, client_ip, target_config
            )

            # Update log data with request details
            log_data["method"] = request_config.get("method", "")
            log_data["path"] = request_config.get("path", "")
            log_data["headers"] = request_config.get("headers", {})
            log_data["body"] = body_data

            # Forward to target API
            target_response, status_code = await self.forward_request(
                request_config, body_data, target_config
            )

            # Update log data with response
            log_data["status"] = status_code
            log_data["target_response"] = target_response

            # Create response based on status code
            expected_success_status = target_config.get("success_status_code", 200)
            is_success = status_code == expected_success_status
            if is_success:
                message = target_config.get(
                    "default_output", "Request forwarded to {target_name} successfully"
                ).format(target_name=target_name)
            else:
                if isinstance(target_response, dict):
                    response_text = json.dumps(
                        target_response, separators=(",", ":")
                    )
                else:
                    response_text = str(target_response)
                message = f"Target API returned status {status_code}: {response_text}"

            response = {
                "statuscode": status_code,
                "success": is_success,
                "message": message,
                "request_id": request_id,
            }

            logger.info(
                f"Successfully processed CMDB request {request_id} for target '{target_name}'"
            )
            return response

        except HTTPException as e:
            log_data["status"] = e.status_code
            log_data["error_message"] = e.detail
            raise

        except Exception as e:
            error_msg = f"Unexpected error processing request {request_id} for target '{target_name}': {str(e)}"
            logger.error(error_msg)
            log_data["status"] = 500
            log_data["error_message"] = error_msg
            raise HTTPException(status_code=500, detail=error_msg)

        finally:
            # Log to database in both success and error paths
            if session is not None:
                try:
                    log_entry = VecmdbTriggerReqLogCreate(**log_data)
                    log_vecmdb_trigger_request(session, log_entry)
                except Exception as e:
                    logger.error(
                        f"Failed to create log entry for request {request_id}: {str(e)}"
                    )


# Global service instance
vecmdb_trigger_service = VecmdbTriggerService()
