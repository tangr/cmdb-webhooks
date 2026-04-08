import httpx
import hashlib
from typing import Dict, Any, List
from urllib.parse import parse_qs, urlparse
from fastapi import HTTPException

from app.services.vecmdb_trigger_service import get_prometheus_sd_configs
from app.utils.logger import get_logger

logger = get_logger(__name__)


class VecmdbPrometheusService:
    """Service for handling Prometheus service discovery operations"""

    def build_api_key(
        self,
        path: str,
        params: Dict[str, Any],
        api_key: str,
        api_secret: str,
    ) -> Dict[str, Any]:
        """Build API authentication parameters for CMDB API"""

        # Build values string from sorted parameters (excluding auth params and complex types)
        values = "".join(
            [
                str(params[k])
                for k in sorted((params or {}).keys())
                if k not in ("_key", "_secret")
                and not isinstance(params[k], (dict, list))
            ]
        )

        # Create signature
        _secret = "".join([path, api_secret, values]).encode("utf-8")
        params["_secret"] = hashlib.sha1(_secret).hexdigest()
        params["_key"] = api_key

        return params

    def get_prometheus_config(self, config_name: str) -> Dict[str, Any]:
        """Get and validate prometheus configuration"""
        configs = get_prometheus_sd_configs()
        if config_name not in configs:
            available_configs = list(configs.keys())
            error_msg = f"Prometheus config '{config_name}' not found. Available configs: {available_configs}"
            logger.error(error_msg)
            raise HTTPException(status_code=404, detail=error_msg)

        return configs[config_name]

    async def fetch_cmdb_data(
        self, prometheus_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fetch CI data from CMDB API with authentication and pagination"""

        cmdb_base_url = prometheus_config.get("cmdb_api_base_url")
        cmdb_path = prometheus_config.get("cmdb_api_path")
        cmdb_query = prometheus_config.get("cmdb_api_query", "")
        cmdb_headers = prometheus_config.get("cmdb_api_headers", {})
        cmdb_api_key = prometheus_config.get("cmdb_api_key")
        cmdb_api_secret = prometheus_config.get("cmdb_api_secret")
        timeout = prometheus_config.get("cmdb_api_timeout", 30)

        if not cmdb_api_key or not cmdb_api_secret:
            error_msg = "CMDB API key and secret are required"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)

        cmdb_url = f"{cmdb_base_url}{cmdb_path}"

        try:
            logger.info(f"Fetching CMDB data from {cmdb_url}")
            logger.debug(f"CMDB query: {cmdb_query}")

            # Parse query string to dict for authentication
            base_query_params = {}
            if cmdb_query:
                parsed_query = parse_qs(cmdb_query)
                base_query_params = {
                    k: v[0] if v else "" for k, v in parsed_query.items()
                }

            # Initialize pagination variables
            page = 1
            all_results = []
            total_found = 0
            page_size = int(base_query_params.get("count", 100))

            async with httpx.AsyncClient(timeout=timeout) as client:
                while True:
                    # Create query params for current page
                    query_params = base_query_params.copy()
                    query_params["page"] = str(page)

                    # Add authentication parameters
                    authenticated_params = self.build_api_key(
                        path=urlparse(cmdb_url).path,
                        params=query_params.copy(),
                        api_key=cmdb_api_key,
                        api_secret=cmdb_api_secret,
                    )

                    logger.debug(
                        f"Fetching page {page} with params: {authenticated_params}"
                    )

                    response = await client.get(
                        url=cmdb_url,
                        params=authenticated_params,
                        headers=cmdb_headers,
                    )

                    logger.debug(
                        f"Page {page} response status: {response.status_code}"
                    )

                    if response.status_code != 200:
                        error_msg = f"CMDB API returned status {response.status_code}: {response.text}"
                        logger.error(error_msg)
                        raise HTTPException(status_code=502, detail=error_msg)

                    try:
                        response_data = response.json()

                        # Update total found from first page
                        if page == 1:
                            total_found = response_data.get("numfound", 0)
                            logger.info(f"Total CI records found: {total_found}")

                        # Add current page results
                        page_results = response_data.get("result", [])
                        all_results.extend(page_results)

                        logger.info(
                            f"Page {page}: got {len(page_results)} records, "
                            f"total collected: {len(all_results)}"
                        )

                        # Check if we have all records
                        if (
                            len(all_results) >= total_found
                            or len(page_results) < page_size
                        ):
                            break

                        page += 1

                    except HTTPException:
                        raise
                    except Exception as e:
                        error_msg = f"Failed to parse CMDB API response on page {page}: {str(e)}"
                        logger.error(error_msg)
                        raise HTTPException(status_code=502, detail=error_msg)

                # Create final response with all results
                final_response = {
                    "numfound": total_found,
                    "total": len(all_results),
                    "page": 1,
                    "result": all_results,
                }

                logger.info(
                    f"Successfully fetched all {len(all_results)} CI records from {page} pages"
                )
                return final_response

        except HTTPException:
            raise

        except httpx.TimeoutException:
            error_msg = f"Timeout while fetching data from CMDB API: {cmdb_url}"
            logger.error(error_msg)
            raise HTTPException(status_code=504, detail=error_msg)

        except httpx.RequestError as e:
            error_msg = (
                f"Request error while fetching from CMDB API {cmdb_url}: {str(e)}"
            )
            logger.error(error_msg)
            raise HTTPException(status_code=502, detail=error_msg)

    def transform_to_prometheus_format(
        self,
        cmdb_data: Dict[str, Any],
        prometheus_config: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Transform CMDB data to Prometheus service discovery format"""

        target_port = prometheus_config.get("target_port", 9100)
        target_field = prometheus_config.get("target_field", "privateIpAddress")
        labels_mapping = prometheus_config.get("labels_mapping", {})
        default_labels = prometheus_config.get("default_labels", {})

        prometheus_targets = []

        for ci_item in cmdb_data.get("result", []):
            ci_dict = ci_item if isinstance(ci_item, dict) else {}
            target_host = ci_dict.get(target_field)

            if not target_host:
                logger.warning(
                    f"CI item missing target field '{target_field}': {ci_dict}"
                )
                continue

            # Build target endpoint
            target_endpoint = f"{target_host}:{target_port}"

            # Build labels from mapping configuration
            item_labels = default_labels.copy()
            for label_key, label_template in labels_mapping.items():
                if (
                    isinstance(label_template, str)
                    and "{{" in label_template
                    and "}}" in label_template
                ):
                    # Template variable substitution
                    label_value = label_template
                    for field_name, field_value in ci_dict.items():
                        if field_value is not None:
                            label_value = label_value.replace(
                                f"{{{{{field_name}}}}}", str(field_value)
                            )
                    item_labels[label_key] = label_value
                else:
                    # Static label value
                    item_labels[label_key] = str(label_template)

            prometheus_target = {
                "targets": [target_endpoint],
                "labels": item_labels,
            }
            prometheus_targets.append(prometheus_target)

            logger.debug(
                f"Generated prometheus target: {target_endpoint} with labels: {item_labels}"
            )

        logger.info(
            f"Generated {len(prometheus_targets)} prometheus target groups "
            f"from {cmdb_data.get('total', 0)} CMDB CIs"
        )
        return prometheus_targets

    async def get_prometheus_sd_config(
        self, config_name: str
    ) -> List[Dict[str, Any]]:
        """Main method to generate Prometheus service discovery configuration"""

        logger.info(f"Generating Prometheus SD config for '{config_name}'")

        try:
            # Get and validate configuration
            prometheus_config = self.get_prometheus_config(config_name)

            # Fetch data from CMDB
            cmdb_data = await self.fetch_cmdb_data(prometheus_config)

            # Transform to Prometheus format
            prometheus_targets = self.transform_to_prometheus_format(
                cmdb_data, prometheus_config
            )

            logger.info(
                f"Successfully generated Prometheus SD config for '{config_name}' "
                f"with {len(prometheus_targets)} target groups"
            )
            return prometheus_targets

        except HTTPException:
            raise

        except Exception as e:
            error_msg = f"Unexpected error generating Prometheus SD config for '{config_name}': {str(e)}"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)


# Global service instance
vecmdb_prometheus_service = VecmdbPrometheusService()
