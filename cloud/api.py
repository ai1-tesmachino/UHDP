from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
import secrets
from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from cloud.auth import (
    issue_user_token,
    require_permission,
    require_station,
    require_user,
    verify_password,
)
from cloud.sync import accept_event_batch


router = APIRouter(prefix="/v1")


class LoginRequest(BaseModel):
    company_id: str = Field(min_length=1, max_length=128)
    username: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=1024)


class EventBatch(BaseModel):
    events: list[dict[str, Any]] = Field(min_length=1, max_length=100)


class UploadRequest(BaseModel):
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class ResolveConflictRequest(BaseModel):
    selected_revision_id: str = Field(min_length=1, max_length=128)


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy", "service": "cloud"}


@router.post("/auth/login")
def login(request: Request, credentials: LoginRequest) -> dict[str, Any]:
    user = request.app.state.database.get_user(
        credentials.company_id,
        credentials.username,
    )
    if (
        user is None
        or not user["active"]
        or not verify_password(credentials.password, user["password_hash"])
    ):
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    token = issue_user_token(
        user["user_id"],
        user["company_id"],
        request.app.state.settings.jwt_secret,
        request.app.state.settings.jwt_lifetime_seconds,
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": request.app.state.settings.jwt_lifetime_seconds,
        "user": {
            "user_id": user["user_id"],
            "company_id": user["company_id"],
            "username": user["username"],
            "role": user["role_id"],
        },
    }


@router.get("/auth/me")
def current_user(user: dict[str, str] = Depends(require_user)) -> dict[str, str]:
    return user


@router.get("/companies/me")
def company_me(
    request: Request,
    user: dict[str, str] = Depends(require_permission("stations:read")),
) -> dict[str, Any]:
    with request.app.state.database.connection() as connection:
        company = connection.execute(
            "SELECT company_id, name, created_at FROM companies WHERE company_id = %s",
            (user["company_id"],),
        ).fetchone()
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found.")
    return dict(company)


@router.get("/stations")
def list_stations(
    request: Request,
    user: dict[str, str] = Depends(require_permission("stations:read")),
) -> list[dict[str, Any]]:
    with request.app.state.database.connection() as connection:
        rows = connection.execute(
            """
            SELECT station_id, name, status, created_at FROM stations
            WHERE company_id = %s ORDER BY station_id
            """,
            (user["company_id"],),
        ).fetchall()
    return [dict(row) for row in rows]


@router.get("/records/sessions/{session_id}/diagnostic-runs")
def diagnostic_run_history(
    session_id: str,
    request: Request,
    user: dict[str, str] = Depends(require_permission("records:read")),
) -> list[dict[str, Any]]:
    with request.app.state.database.connection() as connection:
        rows = connection.execute(
            """
            SELECT run_id, parent_run_id, device_id, diagnostic_type, status,
                   created_at, payload
            FROM diagnostic_runs
            WHERE company_id = %s AND session_id = %s
            ORDER BY created_at, run_id
            """,
            (user["company_id"], session_id),
        ).fetchall()
    return [dict(row) for row in rows]


@router.get("/records/reports")
def list_reports(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    user: dict[str, str] = Depends(require_permission("records:read")),
) -> dict[str, Any]:
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    with request.app.state.database.connection() as connection:
        rows = connection.execute(
            """
            SELECT report_id, session_id, station_id, created_at
            FROM reports WHERE company_id = %s
            ORDER BY created_at DESC LIMIT %s OFFSET %s
            """,
            (user["company_id"], limit, offset),
        ).fetchall()
    return {"items": [dict(row) for row in rows], "limit": limit, "offset": offset}


@router.get("/records/reports/{report_id}")
def get_report(
    report_id: str,
    request: Request,
    user: dict[str, str] = Depends(require_permission("records:read")),
) -> dict[str, Any]:
    with request.app.state.database.connection() as connection:
        row = connection.execute(
            """
            SELECT report_id, session_id, station_id, payload, created_at
            FROM reports WHERE company_id = %s AND report_id = %s
            """,
            (user["company_id"], report_id),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Report not found.")
    return dict(row)


@router.post("/sync/events")
def sync_events(
    request: Request,
    batch: EventBatch,
    station: dict[str, str] = Depends(require_station),
) -> dict[str, Any]:
    return accept_event_batch(request.app.state.database, station, batch.events)


@router.get("/records/sessions")
def list_sessions(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    user: dict[str, str] = Depends(require_permission("records:read")),
) -> dict[str, Any]:
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    with request.app.state.database.connection() as connection:
        rows = connection.execute(
            """
            SELECT session_id, station_id, device_id, latest_revision,
                   identity_snapshot, payload, created_at, updated_at, conflict_state
            FROM qc_sessions WHERE company_id = %s
            ORDER BY created_at DESC LIMIT %s OFFSET %s
            """,
            (user["company_id"], limit, offset),
        ).fetchall()
    return {"items": [dict(row) for row in rows], "limit": limit, "offset": offset}


@router.get("/records/sessions/{session_id}")
def get_session(
    session_id: str,
    request: Request,
    user: dict[str, str] = Depends(require_permission("records:read")),
) -> dict[str, Any]:
    with request.app.state.database.connection() as connection:
        row = connection.execute(
            """
            SELECT session_id, station_id, device_id, latest_revision,
                   identity_snapshot, payload, created_at, updated_at, conflict_state
            FROM qc_sessions WHERE company_id = %s AND session_id = %s
            """,
            (user["company_id"], session_id),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="QC session not found.")
    return dict(row)


@router.get("/records/devices/{device_id}/history")
def device_history(
    device_id: str,
    request: Request,
    user: dict[str, str] = Depends(require_permission("records:read")),
) -> list[dict[str, Any]]:
    with request.app.state.database.connection() as connection:
        rows = connection.execute(
            """
            SELECT session_id, station_id, latest_revision, created_at,
                   updated_at, conflict_state, payload
            FROM qc_sessions
            WHERE company_id = %s AND device_id = %s
            ORDER BY created_at DESC LIMIT 200
            """,
            (user["company_id"], device_id),
        ).fetchall()
    return [dict(row) for row in rows]


@router.get("/records/conflicts")
def list_conflicts(
    request: Request,
    user: dict[str, str] = Depends(require_permission("records:review")),
) -> list[dict[str, Any]]:
    with request.app.state.database.connection() as connection:
        rows = connection.execute(
            """
            SELECT conflicts.conflict_id, conflicts.session_id, conflicts.revision,
                   conflicts.event_id,
                   existing_payload_sha256, incoming_payload_sha256,
                   incoming_payload, detected_at, review_state,
                   (
                       SELECT revision_id FROM qc_session_revisions
                       WHERE company_id = conflicts.company_id
                           AND session_id = conflicts.session_id
                           AND revision = conflicts.revision
                           AND payload_sha256 = conflicts.existing_payload_sha256
                       ORDER BY created_at LIMIT 1
                   ) AS existing_revision_id,
                   (
                       SELECT revision_id FROM qc_session_revisions
                       WHERE company_id = conflicts.company_id
                           AND session_id = conflicts.session_id
                           AND event_id = conflicts.event_id
                       LIMIT 1
                   ) AS incoming_revision_id
            FROM sync_conflicts AS conflicts WHERE company_id = %s
            ORDER BY detected_at DESC LIMIT 200
            """,
            (user["company_id"],),
        ).fetchall()
    return [dict(row) for row in rows]


@router.post("/records/conflicts/{conflict_id}/resolve")
def resolve_conflict(
    conflict_id: str,
    body: ResolveConflictRequest,
    request: Request,
    user: dict[str, str] = Depends(require_permission("records:review")),
) -> dict[str, str]:
    from psycopg.types.json import Jsonb

    with request.app.state.database.connection() as connection:
        conflict = connection.execute(
            """
            SELECT session_id, revision, station_id
            FROM sync_conflicts WHERE company_id = %s AND conflict_id = %s
                AND review_state = 'needs_review'
            FOR UPDATE
            """,
            (user["company_id"], conflict_id),
        ).fetchone()
        if conflict is None:
            raise HTTPException(status_code=404, detail="Open conflict not found.")
        selected = connection.execute(
            """
            SELECT revision, payload FROM qc_session_revisions
            WHERE company_id = %s AND session_id = %s AND revision_id = %s
            """,
            (
                user["company_id"],
                conflict["session_id"],
                body.selected_revision_id,
            ),
        ).fetchone()
        if selected is None or selected["revision"] != conflict["revision"]:
            raise HTTPException(
                status_code=400,
                detail="Selected revision does not belong to this conflict.",
            )
        connection.execute(
            """
            UPDATE qc_sessions SET
                payload = CASE WHEN latest_revision <= %s THEN %s ELSE payload END,
                latest_revision = GREATEST(latest_revision, %s),
                conflict_state = CASE
                    WHEN EXISTS (
                        SELECT 1 FROM sync_conflicts
                        WHERE company_id = %s AND session_id = %s
                            AND review_state = 'needs_review'
                            AND conflict_id <> %s
                    ) THEN 'needs_review'
                    ELSE 'clear'
                END,
                updated_at = now()
            WHERE company_id = %s AND session_id = %s
            """,
            (
                selected["revision"],
                Jsonb(selected["payload"]),
                selected["revision"],
                user["company_id"],
                conflict["session_id"],
                conflict_id,
                user["company_id"],
                conflict["session_id"],
            ),
        )
        connection.execute(
            """
            UPDATE sync_conflicts SET review_state = 'resolved'
            WHERE company_id = %s AND conflict_id = %s
            """,
            (user["company_id"], conflict_id),
        )
        connection.execute(
            """
            INSERT INTO audit_events (
                company_id, audit_event_id, station_id, entity_type, entity_id,
                event_type, payload
            ) VALUES (%s, %s, %s, 'qc_session', %s, 'supervisor_conflict_resolved', %s)
            """,
            (
                user["company_id"],
                str(uuid.uuid4()),
                conflict["station_id"],
                conflict["session_id"],
                Jsonb({
                    "conflict_id": conflict_id,
                    "selected_revision_id": body.selected_revision_id,
                    "reviewed_by": user["user_id"],
                }),
            ),
        )
    return {"conflict_id": conflict_id, "review_state": "resolved"}


@router.get("/analytics/summary")
def analytics_summary(
    request: Request,
    user: dict[str, str] = Depends(require_permission("analytics:read")),
) -> dict[str, Any]:
    with request.app.state.database.connection() as connection:
        sessions = connection.execute(
            """
            SELECT COUNT(*) AS total_sessions,
                   COUNT(*) FILTER (WHERE conflict_state = 'needs_review') AS conflicts,
                   COUNT(DISTINCT device_id) AS distinct_devices
            FROM qc_sessions WHERE company_id = %s
            """,
            (user["company_id"],),
        ).fetchone()
        station_counts = connection.execute(
            """
            SELECT station_id, COUNT(*) AS sessions
            FROM qc_sessions WHERE company_id = %s
            GROUP BY station_id ORDER BY sessions DESC
            """,
            (user["company_id"],),
        ).fetchall()
    return {
        **dict(sessions),
        "sessions_by_station": [dict(row) for row in station_counts],
    }


@router.post("/evidence/{evidence_id}/upload-url")
def evidence_upload_url(
    evidence_id: str,
    request: Request,
    body: UploadRequest,
    station: dict[str, str] = Depends(require_station),
) -> dict[str, Any]:
    client = _object_storage(request)
    company_id = station["company_id"]
    station_id = station["station_id"]
    with request.app.state.database.connection() as connection:
        row = connection.execute(
            """
            SELECT evidence_id, session_id, original_filename, media_type,
                   size_bytes, sha256, upload_state
            FROM evidence_metadata
            WHERE company_id = %s AND evidence_id = %s AND station_id = %s
            """,
            (company_id, evidence_id, station_id),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Evidence metadata not found.")
        if not hmac.compare_digest(str(row["sha256"]), body.sha256):
            raise HTTPException(status_code=409, detail="Evidence checksum mismatch.")
        object_key = f"{company_id}/{evidence_id}"
        connection.execute(
            """
            UPDATE evidence_metadata SET upload_state = 'uploading', object_key = %s
            WHERE company_id = %s AND evidence_id = %s
            """,
            (object_key, company_id, evidence_id),
        )
    checksum = base64.b64encode(bytes.fromhex(body.sha256)).decode("ascii")
    url = client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": request.app.state.object_storage_bucket,
            "Key": object_key,
            "ContentType": row["media_type"],
            "ContentLength": row["size_bytes"],
            "ChecksumSHA256": checksum,
        },
        ExpiresIn=900,
        HttpMethod="PUT",
    )
    return {
        "upload_url": url,
        "method": "PUT",
        "object_key": object_key,
        "expires_in": 900,
        "headers": {
            "Content-Type": row["media_type"],
            "x-amz-checksum-sha256": checksum,
        },
    }


@router.post("/evidence/{evidence_id}/complete")
def complete_evidence_upload(
    evidence_id: str,
    request: Request,
    body: UploadRequest,
    station: dict[str, str] = Depends(require_station),
) -> dict[str, str]:
    from botocore.exceptions import BotoCoreError, ClientError

    client = _object_storage(request)
    company_id = station["company_id"]
    station_id = station["station_id"]
    with request.app.state.database.connection() as connection:
        row = connection.execute(
            """
            SELECT object_key, size_bytes, sha256 FROM evidence_metadata
            WHERE company_id = %s AND evidence_id = %s AND station_id = %s
            """,
            (company_id, evidence_id, station_id),
        ).fetchone()
        if row is None or not row["object_key"]:
            raise HTTPException(status_code=404, detail="Evidence upload was not initialized.")
        if not hmac.compare_digest(str(row["sha256"]), body.sha256):
            raise HTTPException(status_code=409, detail="Evidence checksum mismatch.")
        try:
            stored = client.head_object(
                Bucket=request.app.state.object_storage_bucket,
                Key=row["object_key"],
                ChecksumMode="ENABLED",
            )
        except (BotoCoreError, ClientError) as exc:
            raise HTTPException(status_code=409, detail="Uploaded object is not available.") from exc
        expected_checksum = base64.b64encode(bytes.fromhex(body.sha256)).decode("ascii")
        object_checksum = stored.get("ChecksumSHA256")
        if stored.get("ContentLength") != row["size_bytes"] or object_checksum != expected_checksum:
            raise HTTPException(status_code=409, detail="Uploaded object failed integrity verification.")
        connection.execute(
            """
            UPDATE evidence_metadata SET upload_state = 'synced'
            WHERE company_id = %s AND evidence_id = %s
            """,
            (company_id, evidence_id),
        )
    return {"evidence_id": evidence_id, "upload_state": "synced"}


@router.post("/evidence/{evidence_id}/download-url")
def evidence_download_url(
    evidence_id: str,
    request: Request,
    user: dict[str, str] = Depends(require_permission("evidence:read")),
) -> dict[str, Any]:
    client = _object_storage(request)
    with request.app.state.database.connection() as connection:
        row = connection.execute(
            """
            SELECT object_key, upload_state FROM evidence_metadata
            WHERE company_id = %s AND evidence_id = %s
            """,
            (user["company_id"], evidence_id),
        ).fetchone()
    if row is None or row["upload_state"] != "synced":
        raise HTTPException(status_code=404, detail="Synchronized evidence not found.")
    url = client.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": request.app.state.object_storage_bucket,
            "Key": row["object_key"],
        },
        ExpiresIn=300,
    )
    return {"download_url": url, "expires_in": 300}


def _object_storage(request: Request):
    if request.app.state.object_storage is None:
        raise HTTPException(status_code=503, detail="Cloud object storage is not configured.")
    return request.app.state.object_storage
