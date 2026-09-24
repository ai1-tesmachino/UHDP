from fastapi import APIRouter
from app.api.health.routes import router as health_router
from app.api.sessions.routes import router as session_router

router=APIRouter()
router.include_router(health_router,prefix="/health",tags=["Health"])
router.include_router(session_router,prefix="/sessions",tags=["Sessions"])
