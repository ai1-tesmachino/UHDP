from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.plugins import router as plugins_router
from app.api.router import router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.runtime.application import Application


from app.api.routes.diagnostics import (
    router as diagnostics_router,
)

from app.api.sessions.diagnostic_routes import (
    router as diagnostic_sessions_router,
)

from fastapi.middleware.cors import CORSMiddleware
# from app.api.devices import router as devices_router
from app.api.reports import router as reports_router
from app.api.reports_export import (
    router as reports_export_router,
)

from app.api.profiles import (
    router as profiles_router,
)
from app.api.diagnostic_jobs import router as diagnostic_jobs_router
from app.api.capabilities import router as capabilities_router

settings = get_settings()

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    application = Application()

    await application.start()

    app.state.application = application
    app.state.runtime = application.runtime

    try:
        yield
    finally:
        await application.stop()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    origin.strip()
    for origin in settings.CORS_ORIGINS.split(",")
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    plugins_router,
)

app.include_router(
    diagnostics_router,
)

# app.include_router(
#     devices_router,
# )

app.include_router(
    diagnostic_sessions_router,
)
app.include_router(
    diagnostic_jobs_router,
)
app.include_router(
    capabilities_router,
)

app.include_router(
    router
)

app.include_router(
    reports_router
)
app.include_router(
    reports_export_router
)
app.include_router(
    profiles_router
)