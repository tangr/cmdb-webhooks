from fastapi import Header, HTTPException
from config.config import get_session
from typing import Annotated
from sqlmodel import Session
from fastapi import Depends

SessionDep = Annotated[Session, Depends(get_session)]


async def get_token_header(x_token: str = Header()):
    if x_token != "fake-super-secret-token":
        raise HTTPException(status_code=400, detail="X-Token header invalid")


async def get_query_token(token: str):
    if token != "jessica":
        raise HTTPException(status_code=400, detail="No Jessica token provided")
