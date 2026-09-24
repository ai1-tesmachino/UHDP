from fastapi import FastAPI
from app.api.router import router
from app.core.config import get_settings
from app.core.logging import setup_logging

settings = get_settings()
setup_logging()

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)
app.include_router(router)
