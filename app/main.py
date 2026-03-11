from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, Request
from fastapi.responses import RedirectResponse

from .routers import cmdb_trigger, auth, feishu_bot, gitlab_hook, amis_jenkins, harbor_artifacts
from .dependencies import AuthenticationRequiredException
from config.config import settings
from .services.webhook_mapping import init_webhook_mapping
from .services.gitlab_hook_service import init_gitlab_jenkins_mapping
from .services.amis_jenkins_service import init_amis_jenkins_mapping
from .services.harbor_artifacts_service import init_harbor_config
from fastapi.staticfiles import StaticFiles


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    from app.utils.logger import setup_logging

    setup_logging()
    init_webhook_mapping()
    init_gitlab_jenkins_mapping()
    init_amis_jenkins_mapping()
    init_harbor_config()
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
app.include_router(cmdb_trigger.router, prefix="/cmdb-trigger", tags=["cmdb-trigger"])
app.include_router(feishu_bot.router, prefix="/feishu-bot", tags=["feishu-bot"])
app.include_router(gitlab_hook.router, prefix="/gitlab-hook", tags=["gitlab-hook"])
app.include_router(amis_jenkins.router, prefix="/amis-jenkins", tags=["amis-jenkins"])
app.include_router(harbor_artifacts.router, prefix="/harbor-artifacts", tags=["harbor-artifacts"])

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
