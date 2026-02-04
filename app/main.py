from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, Request
from fastapi.responses import RedirectResponse

from .routers import cmdb, auth, feishu, gitlab
from .dependencies import AuthenticationRequiredException
from config.config import settings
from .services.webhook_mapping import init_webhook_mapping
from .services.gitlab_service import init_gitlab_jenkins_mapping
from fastapi.staticfiles import StaticFiles


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    from app.utils.logger import setup_logging

    setup_logging()
    init_webhook_mapping()
    init_gitlab_jenkins_mapping()
    yield
    # Shutdown (if needed)


app = FastAPI(lifespan=lifespan)


@app.exception_handler(AuthenticationRequiredException)
async def authentication_exception_handler(
    request: Request, exc: AuthenticationRequiredException
):
    """Handle authentication required exceptions by redirecting to login page"""
    return RedirectResponse(url="/auth/login-page", status_code=302)


app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(cmdb.router, prefix="/cmdb", tags=["cmdb"])
app.include_router(feishu.router, prefix="/feishu", tags=["feishu"])
app.include_router(gitlab.router, prefix="/gitlab", tags=["gitlab"])

app.mount("/static", StaticFiles(directory="static"), name="static")


# Convenience redirects for common pages
@app.get("/")
async def root():
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url="/auth/", status_code=302)


@app.get("/login")
async def login_redirect():
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url="/auth/login-page", status_code=302)


@app.get("/dashboard")
async def dashboard_redirect():
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url="/auth/dashboard", status_code=302)
