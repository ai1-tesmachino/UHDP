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

app.include_router(
    plugins_router,
)

app.include_router(
    diagnostics_router,
)

app.include_router(router)
