import httpx
import json
from typing import Dict, Any, Tuple, List
from urllib.parse import parse_qs
from pathlib import Path
from fastapi import HTTPException
import yaml

from app.models.vecmdb_trigger_models import (
    CMDBTriggerRequest,
    TransformedBody,
    ProxyResponse,
)
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
    """Load VecMDB Trigger configuration from YAML file"""
    project_root = _find_project_root()
    config_path = project_root / "config" / "vecmdb_trigger_config.yaml"

    try:
        with open(config_path, "r", encoding="utf-8") as file:
            config = yaml.safe_load(file)
            return config or {}
    except FileNotFoundError:
        logger.warning(f"VecMDB Trigger config file not found at {config_path}")
        return {}
    except yaml.YAMLError as e:
        logger.error(f"Error parsing VecMDB Trigger config YAML: {e}")
        return {}


def init_vecmdb_trigger_config():
    """Initialize VecMDB Trigger configuration on startup"""
    global _vecmdb_trigger_config
    _vecmdb_trigger_config = load_vecmdb_trigger_config()
    api_keys = _vecmdb_trigger_config.get("vecmdb_trigger_webhook_api_keys") or []
    targets = _vecmdb_trigger_config.get("cmdb_trigger_targets") or {}
    prometheus_configs = _vecmdb_trigger_config.get("prometheus_sd_configs") or {}
    logger.info(
        f"Loaded VecMDB Trigger config: "
        f"api_keys={len(api_keys)} key(s), "
        f"cmdb_trigger_targets={len(targets)} target(s), "
        f"prometheus_sd_configs={len(prometheus_configs)} config(s)"
    )


def get_vecmdb_trigger_api_keys() -> List[str]:
    """Get the list of VecMDB Trigger API keys for webhook verification"""
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
        cmdb_request: CMDBTriggerRequest,
        client_ip: str,
        target_config: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], TransformedBody]:
        """Transform CMDB trigger request to separate request config and body"""

        # Get field mappings from target config
        field_mappings = target_config.get("field_mappings", {})
        nodes_mapping_uuid = field_mappings.get("nodes_mapping_uuid", {})
        nodes_mapping_name = field_mappings.get("nodes_mapping_name", {})
        platform_mapping = field_mappings.get("platform_mapping", {})
        default_fields = field_mappings.get("default_fields", {})

        # Apply platform transformation
        transformed_platform = platform_mapping.get(
            cmdb_request.platform, cmdb_request.platform
        )

        # Initialize body data with required fields
        body_data = {"id": cmdb_request.id}

        # Add optional fields if they have values
        if cmdb_request.address:
            body_data["address"] = cmdb_request.address
        if cmdb_request.comment:
            body_data["comment"] = cmdb_request.comment
        if cmdb_request.name:
            body_data["name"] = cmdb_request.name
        if cmdb_request.platform:
            body_data["platform"] = transformed_platform

        # Handle nodes field transformation
        if cmdb_request.nodes:
            node_names = [name.strip() for name in cmdb_request.nodes.split(",")]
            transformed_nodes = []
            for node_name in node_names:
                # Find UUID for each node name in nodes_mapping_uuid
                node_uuid = node_name  # Default to original name if not found
                for uuid, name in nodes_mapping_uuid.items():
                    if name == node_name:
                        node_uuid = uuid
                        break
                transformed_nodes.append(node_uuid)
            body_data["nodes"] = transformed_nodes

        # Handle nodes_display field transformation
        if cmdb_request.nodes_display:
            node_display_names = [
                name.strip() for name in cmdb_request.nodes_display.split(",")
            ]
            transformed_nodes_display = []
            for node_display_name in node_display_names:
                transformed_name = nodes_mapping_name.get(
                    node_display_name, node_display_name
                )
                transformed_nodes_display.append(transformed_name)
            body_data["nodes_display"] = transformed_nodes_display

        # Add default fields from config
        body_data.update(default_fields)

        # Create transformed body
        transformed_body = TransformedBody(**body_data)

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

        logger.info(f"Transformed CMDB request {cmdb_request.id} for target")

        # Log field transformations
        if cmdb_request.nodes:
            logger.debug(
                f"Field transformations: nodes '{cmdb_request.nodes}' -> {body_data.get('nodes')}, "
                f"platform '{cmdb_request.platform}' -> '{transformed_platform}'"
            )
        elif cmdb_request.nodes_display:
            logger.debug(
                f"Field transformations: nodes_display '{cmdb_request.nodes_display}' -> {body_data.get('nodes_display')}, "
                f"platform '{cmdb_request.platform}' -> '{transformed_platform}'"
            )
        else:
            logger.debug(
                f"Field transformations: platform '{cmdb_request.platform}' -> '{transformed_platform}'"
            )

        return request_config, transformed_body

    async def forward_request(
        self,
        request_config: Dict[str, Any],
        transformed_body: TransformedBody,
        target_config: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], int]:
        """Forward transformed request to target API"""

        # Build target URL using config values
        target_api_base_url = target_config.get("target_api_base_url")

        # Build API path with template variable support
        target_api_path = target_config.get("target_api_path", "")
        if target_api_path and "{{" in target_api_path:
            body_dict = transformed_body.model_dump()
            for key, value in body_dict.items():
                if value is not None:
                    target_api_path = target_api_path.replace(
                        f"{{{{{key}}}}}", str(value)
                    )

        target_url = f"{target_api_base_url}{target_api_path}"
        timeout = target_config.get("target_api_timeout", 30)

        try:
            logger.info(
                f"Forwarding request {transformed_body.id} to {target_url}"
            )
            logger.debug(f"Request method: {request_config['method']}")
            logger.debug(f"Request path: {request_config['path']}")
            logger.debug(f"Request query: {request_config['query']}")
            logger.debug(f"Request headers: {request_config['headers']}")
            logger.debug(f"Request body: {transformed_body.model_dump()}")

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
                    json=transformed_body.model_dump(),
                    headers=request_config["headers"],
                )

                logger.info(f"Target API response status: {response.status_code}")
                logger.debug(f"Target API response: {response.text}")

                try:
                    response_data = response.json()
                except Exception:
                    response_data = {"raw_response": response.text}

                logger.info(
                    f"Forwarded request {transformed_body.id} with status {response.status_code}"
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
        cmdb_request: CMDBTriggerRequest,
        client_ip: str,
        target_name: str,
    ) -> ProxyResponse:
        """Main method to process CMDB trigger requests for specific target"""

        logger.info(
            f"Processing CMDB request {cmdb_request.id} from {client_ip} for target '{target_name}'"
        )

        try:
            # Get and validate target configuration
            target_config = self.get_target_config(target_name)

            # Transform request using target-specific configuration
            request_config, transformed_body = self.transform_request(
                cmdb_request, client_ip, target_config
            )

            # Forward to target API
            target_response, status_code = await self.forward_request(
                request_config, transformed_body, target_config
            )

            # Create response based on status code
            expected_success_status = target_config.get("success_status_code", 200)
            is_success = status_code == expected_success_status
            if is_success:
                message = target_config.get(
                    "default_output", "Request forwarded successfully"
                )
            else:
                if isinstance(target_response, dict):
                    response_text = json.dumps(
                        target_response, separators=(",", ":")
                    )
                else:
                    response_text = str(target_response)
                message = f"Target API returned status {status_code}: {response_text}"

            response = ProxyResponse(
                statuscode=status_code,
                success=is_success,
                message=message,
                request_id=cmdb_request.id,
            )

            logger.info(
                f"Successfully processed CMDB request {cmdb_request.id} for target '{target_name}'"
            )
            return response

        except HTTPException:
            raise

        except Exception as e:
            error_msg = f"Unexpected error processing request {cmdb_request.id} for target '{target_name}': {str(e)}"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)


# Global service instance
vecmdb_trigger_service = VecmdbTriggerService()
