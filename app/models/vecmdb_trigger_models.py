from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List


class CMDBTriggerRequest(BaseModel):
    """Model for incoming CMDB trigger requests from veops"""

    address: Optional[str] = Field(None, description="Private IP address from template")
    comment: Optional[str] = Field(None, description="Comment field")
    id: str = Field(..., description="UUID identifier")
    name: Optional[str] = Field(None, description="Name field")
    nodes: Optional[str] = Field(None, description="Node UUID information")
    nodes_display: Optional[str] = Field(
        None, description="Node display name information"
    )
    platform: Optional[str] = Field(None, description="Platform type")


class TransformedBody(BaseModel):
    """Model for the transformed request body (simplified output format)"""

    address: Optional[str] = Field(None, description="Private IP address")
    comment: Optional[str] = Field(None, description="Comment field")
    id: str = Field(..., description="UUID identifier")
    name: Optional[str] = Field(None, description="Name field")
    nodes: Optional[List[str]] = Field(
        default=None, description="Node UUID information"
    )
    nodes_display: Optional[List[str]] = Field(
        default=None, description="Node display name information"
    )
    platform: Optional[str] = Field(None, description="Platform type")

    class Config:
        extra = "allow"

    def model_dump(self, **kwargs):
        """Override model_dump to exclude None values"""
        kwargs.setdefault("exclude_none", True)
        return super().model_dump(**kwargs)


class ProxyResponse(BaseModel):
    """Simple response model for proxy operations"""

    statuscode: int = Field(..., description="HTTP status code from backend")
    success: bool = Field(..., description="Request success status")
    message: str = Field(..., description="Response message")
    request_id: str = Field(..., description="Original request ID")


class CMDBCIItem(BaseModel):
    """Model for CMDB CI item in search results"""

    name: Optional[str] = Field(None, description="CI name")
    privateIpAddress: Optional[str] = Field(None, description="Private IP address")
    treenode: Optional[str] = Field(None, description="Tree node name")
    platformDetails: Optional[str] = Field(None, description="Platform details")

    class Config:
        extra = "allow"


class CMDBSearchResponse(BaseModel):
    """Model for CMDB CI search API response"""

    numfound: int = Field(..., description="Total number of CIs found")
    total: int = Field(..., description="Number of CIs in current page")
    page: int = Field(..., description="Current page number")
    result: List[CMDBCIItem] = Field(..., description="List of CI items")
    facet: Optional[Dict[str, Any]] = Field(
        None, description="Facet aggregation data"
    )
    counter: Optional[Dict[str, Any]] = Field(
        None, description="Counter statistics"
    )


class PrometheusTarget(BaseModel):
    """Model for a single Prometheus service discovery target group"""

    targets: List[str] = Field(..., description="List of target endpoints")
    labels: Dict[str, str] = Field(
        default_factory=dict, description="Labels for this target group"
    )


class BasicAuth(BaseModel):
    """Model for HTTP basic authentication"""

    username: Optional[str] = Field(None, description="Username for basic auth")
    username_file: Optional[str] = Field(
        None, description="Path to file containing username"
    )
    password: Optional[str] = Field(None, description="Password for basic auth")
    password_file: Optional[str] = Field(
        None, description="Path to file containing password"
    )


class Authorization(BaseModel):
    """Model for HTTP authorization header"""

    type: str = Field(default="Bearer", description="Authorization type")
    credentials: Optional[str] = Field(
        None, description="Credentials for authorization"
    )
    credentials_file: Optional[str] = Field(
        None, description="Path to file containing credentials"
    )


class HttpConfig(BaseModel):
    """Model for HTTP configuration including authentication"""

    basic_auth: Optional[BasicAuth] = Field(
        None, description="Basic authentication configuration"
    )
    authorization: Optional[Authorization] = Field(
        None, description="Authorization header configuration"
    )
