from fastapi import APIRouter

from app.diagnostics.capability_catalog import get_capabilities


router = APIRouter(
    prefix="/capabilities",
    tags=["diagnostic-capabilities"],
)


@router.get("/")
def list_capabilities():
    return get_capabilities()
