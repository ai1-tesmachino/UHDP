from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
import logging
import uuid
from typing import Any

from cloud.database import CloudDatabase


logger = logging.getLogger(__name__)


def accept_event_batch(
    database: CloudDatabase,
    station: dict[str, str],
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    accepted: list[str] = []
    rejected: dict[str, str] = {}
    for event in events:
        event_id = str(event.get("event_id", ""))
        try:
            _accept_one(database, station, event)
        except (ValueError, KeyError, TypeError) as exc:
            rejected[event_id or "unknown"] = str(exc)
        except Exception:
            logger.exception("Could not store cloud sync event %s", event_id)
            rejected[event_id or "unknown"] = "Record could not be stored; retry later."
        else:
            accepted.append(event_id)
    return {"accepted_event_ids": accepted, "rejected": rejected}


def _accept_one(
    database: CloudDatabase,
    station: dict[str, str],
    event: dict[str, Any],
) -> None:
    event_id = event.get("event_id")
    event_type = event.get("event_type")
    entity_type = event.get("entity_type")
    entity_id = event.get("entity_id")
    schema_version = event.get("schema_version")
    payload = event.get("payload")
    if not all(
        isinstance(value, str) and value
        for value in (event_id, event_type, entity_type, entity_id)
    ):
        raise ValueError("Event ID, type, entity type, and entity ID are required.")
    if not isinstance(schema_version, int) or schema_version < 1:
        raise ValueError("Event schema version is invalid.")
    if not isinstance(payload, dict):
        raise ValueError("Event payload must be an object.")
    _validate_tenant_snapshot(station, entity_type, payload)

    canonical = json.dumps(event, sort_keys=True, separators=(",", ":"), default=str)
    event_hash = hashlib.sha256(canonical.encode()).hexdigest()
    company_id = station["company_id"]
    station_id = station["station_id"]
    with database.connection() as connection:
        existing = connection.execute(
            """
            SELECT company_id, station_id, payload_sha256
            FROM sync_event_receipts WHERE event_id = %s
            """,
            (event_id,),
        ).fetchone()
        if existing:
            if (
                existing["company_id"] != company_id
                or existing["station_id"] != station_id
                or existing["payload_sha256"] != event_hash
            ):
                raise ValueError("Event ID was already used for a different event.")
            return

        _apply_event(
            database,
            connection,
            station,
            event,
        )
        connection.execute(
            """
            INSERT INTO sync_event_receipts (
                event_id, company_id, station_id, payload_sha256
            ) VALUES (%s, %s, %s, %s)
            """,
            (event_id, company_id, station_id, event_hash),
        )
        created_at = _parse_timestamp(event.get("created_at"))
        connection.execute(
            """
            INSERT INTO audit_events (
                company_id, audit_event_id, station_id, entity_type,
                entity_id, event_type, payload, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                company_id,
                event_id,
                station_id,
                entity_type,
                entity_id,
                event_type,
                _jsonb({"schema_version": schema_version, "payload": payload}),
                created_at,
            ),
        )


def _validate_tenant_snapshot(
    station: dict[str, str],
    entity_type: str,
    event_payload: dict[str, Any],
) -> None:
    data = event_payload.get("data")
    if not isinstance(data, dict):
        data = event_payload
    identity = data.get("identity_snapshot")
    identity = identity if isinstance(identity, dict) else {}
    intake = data.get("intake_record")
    intake = intake if isinstance(intake, dict) else {}
    company_id = identity.get("company_id") or intake.get("company_id")
    station_id = identity.get("station_id") or intake.get("station_id")
    if company_id is not None and company_id != station["company_id"]:
        raise ValueError("Event company does not match the authenticated station.")
    if station_id is not None and station_id != station["station_id"]:
        raise ValueError("Event station does not match the authenticated station.")
    if entity_type not in {
        "session",
        "report",
        "evidence",
        "storage_benchmark",
    }:
        raise ValueError("Unsupported synchronized entity type.")


def _apply_event(
    database: CloudDatabase,
    connection: Any,
    station: dict[str, str],
    event: dict[str, Any],
) -> None:
    from psycopg.types.json import Jsonb

    payload = event["payload"]
    data = payload.get("data")
    data = data if isinstance(data, dict) else payload
    company_id = station["company_id"]
    station_id = station["station_id"]
    event_type = event["event_type"]
    entity_type = event["entity_type"]
    entity_id = event["entity_id"]
    created_at = _parse_timestamp(event.get("created_at"))

    if entity_type == "session":
        _save_session(
            connection,
            station,
            event,
            data,
            Jsonb,
        )
    elif entity_type == "report":
        revision = int(payload.get("revision") or 1)
        digest = _hash(data)
        connection.execute(
            """
            INSERT INTO report_revisions (
                revision_id, company_id, report_id, revision, event_id,
                payload_sha256, payload, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                str(uuid.uuid4()),
                company_id,
                entity_id,
                revision,
                event["event_id"],
                digest,
                Jsonb(data),
                created_at,
            ),
        )
        connection.execute(
            """
            INSERT INTO reports (
                company_id, report_id, session_id, station_id, payload, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (company_id, report_id) DO NOTHING
            """,
            (
                company_id,
                entity_id,
                data.get("session_id"),
                station_id,
                Jsonb(data),
                _parse_timestamp(data.get("created_at")) or created_at,
            ),
        )
    elif entity_type == "evidence":
        connection.execute(
            """
            INSERT INTO evidence_metadata (
                company_id, evidence_id, session_id, run_id, station_id,
                original_filename, media_type, size_bytes, sha256, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (company_id, evidence_id) DO NOTHING
            """,
            (
                company_id,
                entity_id,
                payload.get("session_id"),
                payload.get("run_id"),
                station_id,
                payload.get("original_filename", "evidence.bin"),
                payload.get("media_type", "application/octet-stream"),
                int(payload.get("size_bytes", 0)),
                payload.get("sha256", ""),
                created_at,
            ),
        )
    elif entity_type == "storage_benchmark":
        connection.execute(
            """
            INSERT INTO storage_benchmarks (
                company_id, benchmark_id, device_id, station_id, payload, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (company_id, benchmark_id) DO NOTHING
            """,
            (
                company_id,
                entity_id,
                data.get("device_id", "unknown"),
                station_id,
                Jsonb(data),
                created_at,
            ),
        )

    boot_session_id = payload.get("boot_session_id")
    if not isinstance(boot_session_id, str):
        boot_session_id = event.get("boot_session_id")
    if isinstance(boot_session_id, str) and boot_session_id:
        connection.execute(
            """
            INSERT INTO boot_sessions (
                company_id, boot_session_id, station_id, started_at, payload
            ) VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (company_id, boot_session_id) DO NOTHING
            """,
            (
                company_id,
                boot_session_id,
                station_id,
                created_at,
                Jsonb({"software_version": payload.get("software_version")}),
            ),
        )


def _save_session(
    connection: Any,
    station: dict[str, str],
    event: dict[str, Any],
    data: dict[str, Any],
    jsonb: Any,
) -> None:
    company_id = station["company_id"]
    station_id = station["station_id"]
    session_id = event["entity_id"]
    revision = int(event["payload"].get("revision") or 1)
    digest = _hash(data)
    identity = data.get("identity_snapshot")
    if not isinstance(identity, dict):
        intake = data.get("intake_record")
        intake = intake if isinstance(intake, dict) else {}
        identity = {
            "company_id": company_id,
            "station_id": station_id,
            "technician": intake.get("technician"),
        }
    identity = {**identity, "company_id": company_id, "station_id": station_id}
    existing_same_revision = connection.execute(
        """
        SELECT payload_sha256 FROM qc_session_revisions
        WHERE company_id = %s AND session_id = %s AND revision = %s
        """,
        (company_id, session_id, revision),
    ).fetchall()
    conflict = any(row["payload_sha256"] != digest for row in existing_same_revision)
    connection.execute(
        """
        INSERT INTO qc_session_revisions (
            revision_id, company_id, session_id, station_id, revision,
            event_id, payload_sha256, payload, conflict
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            str(uuid.uuid4()),
            company_id,
            session_id,
            station_id,
            revision,
            event["event_id"],
            digest,
            jsonb(data),
            conflict,
        ),
    )
    created_at = _parse_timestamp(data.get("created_at"))
    if not existing_same_revision:
        connection.execute(
            """
            INSERT INTO qc_sessions (
                company_id, session_id, station_id, device_id, latest_revision,
                identity_snapshot, payload, created_at, conflict_state
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'clear')
            ON CONFLICT (company_id, session_id) DO UPDATE SET
                device_id = COALESCE(EXCLUDED.device_id, qc_sessions.device_id),
                latest_revision = GREATEST(qc_sessions.latest_revision, EXCLUDED.latest_revision),
                payload = CASE
                    WHEN EXCLUDED.latest_revision > qc_sessions.latest_revision
                    THEN EXCLUDED.payload
                    ELSE qc_sessions.payload
                END,
                updated_at = now()
            """,
            (
                company_id,
                session_id,
                station_id,
                data.get("device_id"),
                revision,
                jsonb(identity),
                jsonb(data),
                created_at,
            ),
        )
    elif conflict:
        existing_hash = existing_same_revision[0]["payload_sha256"]
        connection.execute(
            """
            INSERT INTO sync_conflicts (
                conflict_id, company_id, session_id, station_id, revision, event_id,
                existing_payload_sha256, incoming_payload_sha256, incoming_payload
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                str(uuid.uuid4()),
                company_id,
                session_id,
                station_id,
                revision,
                event["event_id"],
                existing_hash,
                digest,
                jsonb(data),
            ),
        )
        connection.execute(
            """
            UPDATE qc_sessions SET conflict_state = 'needs_review', updated_at = now()
            WHERE company_id = %s AND session_id = %s
            """,
            (company_id, session_id),
        )

    for device in data.get("discovered_devices", []):
        if not isinstance(device, dict) or not isinstance(device.get("device_id"), str):
            continue
        connection.execute(
            """
            INSERT INTO devices (company_id, device_id, payload)
            VALUES (%s, %s, %s)
            ON CONFLICT (company_id, device_id) DO UPDATE SET
                payload = EXCLUDED.payload, updated_at = now()
            """,
            (company_id, device["device_id"], jsonb(device)),
        )

    collection = data.get("diagnostic_results")
    results = collection.get("results", []) if isinstance(collection, dict) else []
    for result in results if isinstance(results, list) else []:
        if not isinstance(result, dict):
            continue
        run_id = result.get("diagnostic_id")
        diagnostic_type = result.get("diagnostic_type")
        if not isinstance(run_id, str) or not isinstance(diagnostic_type, str):
            continue
        run_created = _parse_timestamp(result.get("created_at"))
        status_value = result.get("status", "unknown")
        if isinstance(status_value, dict):
            status_value = status_value.get("value", "unknown")
        connection.execute(
            """
            INSERT INTO diagnostic_runs (
                company_id, run_id, session_id, parent_run_id, station_id,
                device_id, diagnostic_type, status, created_at, payload
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (company_id, run_id) DO NOTHING
            """,
            (
                company_id,
                run_id,
                session_id,
                (result.get("details") or {}).get("parent_run_id")
                if isinstance(result.get("details"), dict)
                else None,
                station_id,
                result.get("device_id"),
                diagnostic_type,
                str(status_value),
                run_created,
                jsonb(result),
            ),
        )
        connection.execute(
            """
            INSERT INTO diagnostic_results (
                company_id, result_id, run_id, session_id, payload, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (company_id, result_id) DO NOTHING
            """,
            (company_id, run_id, run_id, session_id, jsonb(result), run_created),
        )


def _parse_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except ValueError:
            pass
    return datetime.now(UTC)


def _hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode()).hexdigest()


def _jsonb(value: Any) -> Any:
    from psycopg.types.json import Jsonb

    return Jsonb(value)
