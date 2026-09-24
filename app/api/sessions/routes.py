from fastapi import APIRouter, Depends
from app.core.dependencies import get_session_service

router=APIRouter()

@router.post("/")
async def create_session(service=Depends(get_session_service)):
    return service.create().model_dump()
