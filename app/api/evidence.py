from __future__ import annotations

import asyncio
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask
from starlette.concurrency import run_in_threadpool
import tempfile

from app.core.config import get_settings
from app.evidence.storage import EvidenceStorage
from app.persistence.local.database import SQLiteDatabase


router = APIRouter(prefix="/evidence", tags=["evidence"])
_ALLOWED_MEDIA_TYPES = {
    "application/json",
    "application/pdf",
    "application/octet-stream",
    "image/jpeg",
    "image/png",
    "image/webp",
    "text/plain",
    "text/csv",
    "video/mp4",
    "video/webm",
}


def _require_sqlite() -> SQLiteDatabase:
    if get_settings().STORAGE_BACKEND != "sqlite":
        raise HTTPException(
            status_code=409,
            detail="Persistent evidence requires STORAGE_BACKEND=sqlite.",
        )
    return SQLiteDatabase()


@router.post("/{session_id}")
async def upload_evidence(
    session_id: str,
    request: Request,
    run_id: str | None = None,
) -> dict:
    database = _require_sqlite()
    if request.headers.get("x-uhdp-confirmed") != "true":
        raise HTTPException(
            status_code=400,
            detail="Technician confirmation is required before saving evidence.",
        )
    media_type = request.headers.get("content-type", "").split(";", 1)[0].lower()
    if media_type not in _ALLOWED_MEDIA_TYPES:
        raise HTTPException(status_code=415, detail="Unsupported evidence media type.")
    filename = request.headers.get("x-filename", "evidence.bin")
    maximum = get_settings().EVIDENCE_MAX_FILE_BYTES
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            if int(content_length) > maximum:
                raise HTTPException(status_code=413, detail="Evidence file is too large.")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid Content-Length.") from exc

    size = 0
    with tempfile.TemporaryFile(mode="w+b") as incoming:
        async for chunk in request.stream():
            size += len(chunk)
            if size > maximum:
                raise HTTPException(status_code=413, detail="Evidence file is too large.")
            await asyncio.to_thread(incoming.write, chunk)
        await asyncio.to_thread(incoming.seek, 0)
        storage = EvidenceStorage(
            database=database,
            max_file_bytes=maximum,
        )
        try:
            metadata = await run_in_threadpool(
                storage.store,
                session_id,
                incoming,
                filename=filename,
                media_type=media_type,
                run_id=run_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    from app.services.diagnostic_session_service import (
        diagnostic_session_service,
    )

    await run_in_threadpool(
        diagnostic_session_service.refresh_report_for_session,
        session_id,
    )
    return metadata


@router.get("/session/{session_id}")
def list_session_evidence(session_id: str) -> list[dict]:
    return _require_sqlite().list_evidence(session_id)


@router.get("/{evidence_id}")
def download_evidence(evidence_id: str):
    storage = EvidenceStorage(database=_require_sqlite())
    try:
        metadata, stream = storage.open(evidence_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Evidence not found.") from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=500,
            detail="Stored evidence failed path or integrity verification.",
        ) from exc
    filename = str(metadata["original_filename"]).replace('"', "")
    return StreamingResponse(
        stream,
        media_type=str(metadata["media_type"]),
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        background=BackgroundTask(stream.close),
    )
