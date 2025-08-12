from fastapi import Depends, FastAPI

from .dependencies import get_query_token, get_token_header
from .internal import admin
from .routers import items, users, jms_reqlog, auth
from config.config import settings
from fastapi.staticfiles import StaticFiles

# app = FastAPI(dependencies=[Depends(get_query_token)])
app = FastAPI()


app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(users.router)
app.include_router(items.router)
app.include_router(jms_reqlog.router, prefix="/jms_reqlog", tags=["jms_reqlog"])
app.include_router(
    admin.router,
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_token_header)],
    responses={418: {"description": "I'm a teapot"}},
)
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
