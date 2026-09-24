from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import router
from app.core.config import get_settings
from app.core.logging import setup_logging

from app.runtime.context import RuntimeContext

from app.api.plugins import router as plugins_router




settings = get_settings()

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    runtime = RuntimeContext()

    await runtime.start()

    app.state.runtime = runtime

    yield

    await runtime.stop()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.include_router(
    plugins_router,
)



app.include_router(router)