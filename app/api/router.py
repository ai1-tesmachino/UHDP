from fastapi import APIRouter

from app.api.health.routes import (
    router as health_router,
)

from app.api.sessions.routes import (
    router as session_router,
)

from app.api.workflows.routes import (
    router as workflow_router,
)

router = APIRouter()



router.include_router(
    health_router,
    prefix="/health",
    tags=["Health"],
)

router.include_router(
    session_router,
    prefix="/sessions",
    tags=["Sessions"],
)

router.include_router(
    workflow_router,
    prefix="/workflows",
    tags=["Workflows"],
)