from pydantic import BaseModel, Field
from typing import Optional


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
