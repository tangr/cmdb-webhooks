from fastapi import APIRouter, Depends, HTTPException, Query
from app.dependencies import get_current_user_any_required, User
from app.services.harbor_artifacts_service import (
    fetch_artifacts,
    format_artifacts_for_amis,
    get_default_page_size,
    get_max_page_size,
    get_harbor_config,
)
from typing import Optional
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("")
async def get_artifacts(
    project: str = Query(..., description="Harbor project name"),
    repo: str = Query(..., description="Repository name within the project"),
    instance: Optional[str] = Query(
        None, description="Harbor instance ID (uses default if not specified)"
    ),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(50, ge=1, le=100, description="Number of items per page"),
    current_user: User = Depends(get_current_user_any_required),
):
    """
    Get container image artifacts from Harbor registry.

    Returns data formatted for Amis select input component.

    **Authentication Required**: JWT, Session, or OIDC token

    **Query Parameters**:
    - `project`: Harbor project name (required)
    - `repo`: Repository name (required)
    - `instance`: Harbor instance ID from config (optional, uses default)
    - `page`: Page number, starting from 1
    - `page_size`: Items per page (max 100)

    **Response Format** (Amis compatible):
    ```json
    {
        "status": 0,
        "msg": "success",
        "data": {
            "options": [
                {"label": "v1.0.0 (2024-03-10 14:30)", "value": "project/repo:v1.0.0"}
            ],
            "hasMore": true,
            "page": 1,
            "pageSize": 50
        }
    }
    ```
    """
    logger.info(
        f"User '{current_user.username}' fetching artifacts: "
        f"instance={instance}, project={project}, repo={repo}, page={page}"
    )

    # Cap page_size to max allowed
    max_size = get_max_page_size()
    if page_size > max_size:
        page_size = max_size

    # Fetch artifacts from Harbor
    result = await fetch_artifacts(
        instance_id=instance,
        project=project,
        repo=repo,
        page=page,
        page_size=page_size,
    )

    # Check for errors
    if "error" in result:
        error_msg = result["error"]
        logger.warning(f"Harbor API error: {error_msg}")

        # Determine appropriate status code
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg)
        elif "authentication" in error_msg.lower() or "denied" in error_msg.lower():
            raise HTTPException(status_code=502, detail=error_msg)
        elif "timed out" in error_msg.lower():
            raise HTTPException(status_code=504, detail=error_msg)
        elif "instance" in error_msg.lower() and "not found" in error_msg.lower():
            raise HTTPException(
                status_code=400,
                detail={
                    "message": error_msg,
                    "available_instances": result.get("available_instances", []),
                },
            )
        else:
            raise HTTPException(status_code=502, detail=error_msg)

    # Format artifacts for Amis select
    artifacts = result.get("artifacts", [])
    options = format_artifacts_for_amis(artifacts, project, repo)

    logger.info(f"Returning {len(options)} artifact options for {project}/{repo}")

    # Return Amis compatible response
    return {
        "status": 0,
        "msg": "success",
        "data": {
            "options": options,
            "hasMore": result.get("has_more", False),
            "page": result.get("page", page),
            "pageSize": result.get("page_size", page_size),
            "totalCount": result.get("total_count"),
        },
    }


@router.get("/instances")
async def list_instances(
    current_user: User = Depends(get_current_user_any_required),
):
    """
    List available Harbor instances.

    **Authentication Required**: JWT, Session, or OIDC token

    Returns list of configured Harbor instance IDs.
    """
    config = get_harbor_config()
    instances = config.get("instances") or {}
    default_instance = config.get("default_instance", "")

    return {
        "status": 0,
        "msg": "success",
        "data": {
            "instances": list(instances.keys()),
            "default": default_instance,
        },
    }
