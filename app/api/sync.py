from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import get_settings
from app.persistence.local.database import SQLiteDatabase


router = APIRouter(prefix="/sync", tags=["sync"])


class RetryRequest(BaseModel):
    event_id: str | None = None


@router.get("/status")
def get_sync_status() -> dict:
    if get_settings().STORAGE_BACKEND != "sqlite":
        return {
            "enabled": False,
            "states": {
                "Pending": 0,
                "Syncing": 0,
                "Synced": 0,
                "Needs attention": 0,
            },
            "last_successful_sync": None,
            "failed_events": [],
            "cloud_configured": False,
        }
    return SQLiteDatabase().sync_status()


@router.get("/entity/{entity_type}/{entity_id}")
def get_entity_sync_status(entity_type: str, entity_id: str) -> dict:
    if entity_type not in {"session", "report", "evidence", "storage_benchmark"}:
        raise HTTPException(status_code=400, detail="Unsupported sync entity type.")
    if get_settings().STORAGE_BACKEND != "sqlite":
        raise HTTPException(
            status_code=409,
            detail="Local SQLite persistence is not enabled.",
        )
    return SQLiteDatabase().entity_sync_status(entity_type, entity_id)


@router.post("/retry")
def retry_sync(request: RetryRequest) -> dict[str, int]:
    if get_settings().STORAGE_BACKEND != "sqlite":
        raise HTTPException(
            status_code=409,
            detail="Local SQLite persistence is not enabled.",
        )
    retried = SQLiteDatabase().retry_sync(request.event_id)
    if request.event_id is not None and retried == 0:
        raise HTTPException(
            status_code=404,
            detail="No event needing attention was found with that ID.",
        )
    return {"retried": retried}
