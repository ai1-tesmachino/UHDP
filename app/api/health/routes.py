from fastapi import APIRouter, Depends

from app.api.dependencies import get_runtime
from app.runtime.context import RuntimeContext


router = APIRouter()


@router.get("/")
async def health(
    runtime: RuntimeContext = Depends(get_runtime),
):
    return {
        "status": "healthy",
        "runtime": runtime.lifecycle_manager.get_status().value,
    }
