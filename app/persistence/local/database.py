from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sqlite3
import sys
from typing import Any, Iterator
import uuid

from app.core.config import get_settings


class SQLiteDatabase:
    """SQLite connection and versioned-schema management for local records."""

    def __init__(self, path: str | Path | None = None) -> None:
        settings = get_settings()
        configured_path = path or settings.SQLITE_DATABASE_PATH
        self.path = Path(configured_path or Path(settings.DATA_DIR) / "uhdp.sqlite3")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(descriptor)
        os.chmod(self.path, 0o600)
        self._migrate()
        self.boot_session_id = _current_boot_session_id()
        with self.connection() as connection:
            latest_migration = connection.execute(
                "SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1"
            ).fetchone()
            self.schema_version = (
                int(str(latest_migration["version"]).split("_", 1)[0])
                if latest_migration
                else 0
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO boot_sessions (
                    boot_session_id, started_at, software_version, schema_version
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    self.boot_session_id,
                    datetime.now(UTC).isoformat(),
                    settings.APP_VERSION,
                    self.schema_version,
                ),
            )

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 30000")
        connection.execute("PRAGMA synchronous = FULL")
        try:
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    def save_session(
        self,
        session_id: str,
        payload: dict[str, Any],
        *,
        enqueue_sync: bool = True,
        only_if_missing: bool = False,
    ) -> bool:
        now = datetime.now(UTC).isoformat()
        serialized = _serialize(payload)
        with self.connection() as connection:
            row = connection.execute(
                "SELECT created_at FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if only_if_missing and row is not None:
                return False
            created_at = (
                str(payload.get("created_at") or now)
                if row is None
                else row["created_at"]
            )
            connection.execute(
                """
                INSERT INTO sessions (
                    session_id, payload_json, created_at, updated_at, deleted_at
                ) VALUES (?, ?, ?, ?, NULL)
                ON CONFLICT(session_id) DO UPDATE SET
                    payload_json = excluded.payload_json,
                    updated_at = excluded.updated_at,
                    deleted_at = NULL
                """,
                (session_id, serialized, created_at, now),
            )
            revision = connection.execute(
                """
                SELECT COALESCE(MAX(revision), 0) + 1
                FROM session_revisions WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()[0]
            connection.execute(
                """
                INSERT INTO session_revisions (
                    revision_id, session_id, revision, created_at, payload_json
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (str(uuid.uuid4()), session_id, revision, now, serialized),
            )
            identity_snapshot = _session_identity_snapshot(payload)
            company_id = identity_snapshot.get("company_id")
            intake = payload.get("intake_record")
            intake = intake if isinstance(intake, dict) else {}
            station_id = identity_snapshot.get("station_id")
            device_id = payload.get("device_id")
            if not isinstance(device_id, str):
                device_id = None
            settings = get_settings()
            connection.execute(
                """
                INSERT INTO qc_sessions (
                    session_id, boot_session_id, device_id, company_id, station_id,
                    identity_snapshot_json, software_version, catalogue_version,
                    schema_version, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    device_id = excluded.device_id,
                    updated_at = excluded.updated_at
                """,
                (
                    session_id,
                    self.boot_session_id,
                    device_id,
                    company_id,
                    station_id,
                    _serialize(identity_snapshot),
                    settings.APP_VERSION,
                    payload.get("diagnostic_catalogue_version"),
                    self.schema_version,
                    created_at,
                    now,
                ),
            )
            asset_id = payload.get("asset_id")
            if asset_id is not None and (
                not isinstance(asset_id, str) or not asset_id
            ):
                raise ValueError("A non-empty asset_id is required when supplied.")
            if isinstance(asset_id, str):
                self._persist_session_asset(
                    connection,
                    session_id,
                    asset_id,
                    payload.get("asset"),
                    created_at,
                    now,
                )
                self._persist_session_components(
                    connection,
                    asset_id,
                    payload.get("components"),
                    now,
                )
            elif payload.get("components"):
                raise ValueError("Components cannot be stored without a session asset.")
            else:
                existing_asset_link = connection.execute(
                    "SELECT 1 FROM session_asset_links WHERE session_id = ?",
                    (session_id,),
                ).fetchone()
                if existing_asset_link is not None:
                    raise ValueError("A QC session cannot lose its canonical asset.")
            self._persist_session_devices(connection, payload, company_id, now)
            self._persist_diagnostic_runs(
                connection,
                session_id,
                payload,
                now,
                asset_id if isinstance(asset_id, str) else None,
            )
            self._append_audit(
                connection,
                "qc_session",
                session_id,
                "created" if row is None else "revised",
                identity_snapshot,
                {"revision": revision},
                now,
            )
            if enqueue_sync:
                self._enqueue(
                    connection,
                    "session.created" if row is None else "session.updated",
                    "session",
                    session_id,
                    {
                        "session_id": session_id,
                        "revision": revision,
                        "data": payload,
                        "boot_session_id": self.boot_session_id,
                        "software_version": settings.APP_VERSION,
                        "schema_version": self.schema_version,
                    },
                    now,
                    self.boot_session_id,
                )
        return True

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        with self.connection() as connection:
            row = connection.execute(
                """
                SELECT payload_json FROM sessions
                WHERE session_id = ? AND deleted_at IS NULL
                """,
                (session_id,),
            ).fetchone()
        return _deserialize(row["payload_json"]) if row else None

    def list_sessions(self) -> list[dict[str, Any]]:
        with self.connection() as connection:
            rows = connection.execute(
                """
                SELECT payload_json FROM sessions
                WHERE deleted_at IS NULL ORDER BY created_at, session_id
                """
            ).fetchall()
        return [_deserialize(row["payload_json"]) for row in rows]

    def delete_session(self, session_id: str) -> None:
        now = datetime.now(UTC).isoformat()
        with self.connection() as connection:
            row = connection.execute(
                """
                SELECT payload_json FROM sessions
                WHERE session_id = ? AND deleted_at IS NULL
                """,
                (session_id,),
            ).fetchone()
            if row is None:
                return
            connection.execute(
                "UPDATE sessions SET deleted_at = ?, updated_at = ? WHERE session_id = ?",
                (now, now, session_id),
            )
            self._enqueue(
                connection,
                "session.deleted",
                "session",
                session_id,
                {"session_id": session_id, "data": _deserialize(row["payload_json"])},
                now,
                self.boot_session_id,
            )

    def get_station_inventory(self, inventory_id: str) -> dict[str, Any] | None:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT payload_json FROM station_inventory WHERE inventory_id = ?",
                (inventory_id,),
            ).fetchone()
        return _deserialize(row["payload_json"]) if row else None

    def save_station_inventory(
        self,
        inventory_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        updated_at = datetime.now(UTC).isoformat()
        record = {**payload, "updated_at": updated_at}
        with self.connection() as connection:
            connection.execute(
                """
                INSERT INTO station_inventory (inventory_id, payload_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(inventory_id) DO UPDATE SET
                    payload_json = excluded.payload_json,
                    updated_at = excluded.updated_at
                """,
                (inventory_id, _serialize(record), updated_at),
            )
        return record

    def save_report(
        self,
        report_id: str,
        payload: dict[str, Any],
        html: str | None,
        *,
        enqueue_sync: bool = True,
        only_if_missing: bool = False,
    ) -> bool:
        now = datetime.now(UTC).isoformat()
        report_payload = dict(payload)
        with self.connection() as connection:
            row = connection.execute(
                "SELECT created_at FROM reports WHERE report_id = ?",
                (report_id,),
            ).fetchone()
            if only_if_missing and row is not None:
                return False
            latest = connection.execute(
                """
                SELECT revision_id, finalized_at
                FROM report_revisions
                WHERE report_id = ?
                ORDER BY revision DESC LIMIT 1
                """,
                (report_id,),
            ).fetchone()
            revision_id = report_payload.get("revision_id")
            if not isinstance(revision_id, str) or not revision_id:
                revision_id = str(uuid.uuid4())
            report_payload["revision_id"] = revision_id
            serialized = _serialize(report_payload)
            existing_revision = connection.execute(
                """
                SELECT report_id, payload_json, payload_html
                FROM report_revisions WHERE revision_id = ?
                """,
                (revision_id,),
            ).fetchone()
            if existing_revision is not None:
                if (
                    existing_revision["report_id"] == report_id
                    and existing_revision["payload_json"] == serialized
                    and existing_revision["payload_html"] == html
                ):
                    return False
                raise ValueError(
                    f"Report revision_id already exists: {revision_id}"
                )
            supersedes_revision_id = report_payload.get(
                "supersedes_revision_id"
            )
            supersession_reason = report_payload.get("supersession_reason")
            superseded_by = report_payload.get("superseded_by")
            if latest is not None and latest["finalized_at"] is not None:
                if (
                    supersedes_revision_id != latest["revision_id"]
                    or not isinstance(supersession_reason, str)
                    or not supersession_reason.strip()
                    or not isinstance(superseded_by, str)
                    or not superseded_by.strip()
                ):
                    raise ValueError(
                        "A finalized report requires an explicit, attributed superseding revision."
                    )
            elif any(
                value is not None
                for value in (
                    supersedes_revision_id,
                    supersession_reason,
                    superseded_by,
                )
            ):
                raise ValueError(
                    "A report can supersede only a finalized revision."
                )
            created_at = (
                str(report_payload.get("created_at") or now)
                if row is None
                else row["created_at"]
            )
            connection.execute(
                """
                INSERT INTO reports (
                    report_id, payload_json, payload_html, created_at, updated_at,
                    deleted_at
                ) VALUES (?, ?, ?, ?, ?, NULL)
                ON CONFLICT(report_id) DO UPDATE SET
                    payload_json = excluded.payload_json,
                    payload_html = excluded.payload_html,
                    updated_at = excluded.updated_at,
                    deleted_at = NULL
                """,
                (report_id, serialized, html, created_at, now),
            )
            revision = connection.execute(
                """
                SELECT COALESCE(MAX(revision), 0) + 1
                FROM report_revisions WHERE report_id = ?
                """,
                (report_id,),
            ).fetchone()[0]
            connection.execute(
                """
                INSERT INTO report_revisions (
                    revision_id, report_id, revision, created_at, payload_json,
                    payload_html, supersedes_revision_id, supersession_reason,
                    finalized_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    revision_id,
                    report_id,
                    revision,
                    now,
                    serialized,
                    html,
                    supersedes_revision_id,
                    supersession_reason,
                    superseded_by,
                ),
            )
            if enqueue_sync:
                self._enqueue(
                    connection,
                    "report.created" if row is None else "report.updated",
                    "report",
                    report_id,
                    {
                        "report_id": report_id,
                        "revision": revision,
                        "data": report_payload,
                        "boot_session_id": self.boot_session_id,
                        "software_version": get_settings().APP_VERSION,
                        "schema_version": self.schema_version,
                    },
                    now,
                    self.boot_session_id,
                )
        return True

    def get_asset(self, asset_id: str) -> dict[str, Any] | None:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT payload_json FROM assets WHERE asset_id = ?",
                (asset_id,),
            ).fetchone()
        return _deserialize(row["payload_json"]) if row else None

    def get_report_json(self, report_id: str) -> dict[str, Any] | None:
        with self.connection() as connection:
            row = connection.execute(
                """
                SELECT payload_json FROM reports
                WHERE report_id = ? AND deleted_at IS NULL
                """,
                (report_id,),
            ).fetchone()
            revision = connection.execute(
                """
                SELECT finalized_at, finalized_by
                FROM report_revisions
                WHERE report_id = ?
                ORDER BY revision DESC LIMIT 1
                """,
                (report_id,),
            ).fetchone()
        if row is None:
            return None
        payload = _deserialize(row["payload_json"])
        if revision is not None:
            payload["finalized_at"] = revision["finalized_at"]
            payload["finalized_by"] = revision["finalized_by"]
        return payload

    def get_report_html(self, report_id: str) -> str | None:
        with self.connection() as connection:
            row = connection.execute(
                """
                SELECT payload_html FROM reports
                WHERE report_id = ? AND deleted_at IS NULL
                """,
                (report_id,),
            ).fetchone()
        return row["payload_html"] if row else None

    def latest_report_revision(
        self,
        report_id: str,
    ) -> tuple[int, dict[str, Any], str | None] | None:
        with self.connection() as connection:
            row = connection.execute(
                """
                SELECT revision, payload_json, payload_html
                FROM report_revisions
                WHERE report_id = ?
                ORDER BY revision DESC LIMIT 1
                """,
                (report_id,),
            ).fetchone()
        if row is None:
            return None
        return (
            int(row["revision"]),
            _deserialize(row["payload_json"]),
            row["payload_html"],
        )

    def list_report_revisions(self, report_id: str) -> list[dict[str, Any]]:
        with self.connection() as connection:
            rows = connection.execute(
                """
                SELECT revision_id, revision, created_at, payload_json,
                       payload_html, finalized_at, finalized_by,
                       supersedes_revision_id, supersession_reason
                FROM report_revisions
                WHERE report_id = ?
                ORDER BY revision
                """,
                (report_id,),
            ).fetchall()
        revisions = []
        for row in rows:
            payload = _deserialize(row["payload_json"])
            payload.update(
                revision=row["revision"],
                revision_id=row["revision_id"],
                created_at=row["created_at"],
                finalized_at=row["finalized_at"],
                finalized_by=row["finalized_by"],
                supersedes_revision_id=row["supersedes_revision_id"],
                supersession_reason=row["supersession_reason"],
                html=row["payload_html"],
            )
            revisions.append(payload)
        return revisions

    def finalize_report(
        self,
        report_id: str,
        revision_id: str,
        finalized_by: str | None,
    ) -> dict[str, Any]:
        now = datetime.now(UTC).isoformat()
        with self.connection() as connection:
            latest = connection.execute(
                """
                SELECT revision_id, finalized_at, finalized_by
                FROM report_revisions
                WHERE report_id = ?
                ORDER BY revision DESC LIMIT 1
                """,
                (report_id,),
            ).fetchone()
            if latest is None or latest["revision_id"] != revision_id:
                raise ValueError(
                    "Only the latest report revision can be finalized."
                )
            if latest["finalized_at"] is None:
                connection.execute(
                    """
                    UPDATE report_revisions
                    SET finalized_at = ?, finalized_by = ?
                    WHERE revision_id = ?
                    """,
                    (now, finalized_by, revision_id),
                )
                return {"finalized_at": now, "finalized_by": finalized_by}
            return {
                "finalized_at": latest["finalized_at"],
                "finalized_by": latest["finalized_by"],
            }

    def list_reports(self) -> list[str]:
        with self.connection() as connection:
            rows = connection.execute(
                """
                SELECT report_id FROM reports
                WHERE deleted_at IS NULL ORDER BY report_id
                """
            ).fetchall()
        return [row["report_id"] for row in rows]

    def save_evidence_metadata(
        self,
        *,
        evidence_id: str,
        session_id: str,
        run_id: str | None,
        relative_path: str,
        original_filename: str,
        media_type: str,
        size_bytes: int,
        sha256: str,
    ) -> dict[str, Any]:
        now = datetime.now(UTC).isoformat()
        metadata = {
            "evidence_id": evidence_id,
            "session_id": session_id,
            "run_id": run_id,
            "original_filename": original_filename,
            "media_type": media_type,
            "size_bytes": size_bytes,
            "sha256": sha256,
            "created_at": now,
        }
        with self.connection() as connection:
            session = connection.execute(
                "SELECT identity_snapshot_json FROM qc_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if session is None:
                raise ValueError(f"QC session not found: {session_id}")
            if run_id is not None:
                run = connection.execute(
                    "SELECT 1 FROM diagnostic_runs WHERE run_id = ? AND session_id = ?",
                    (run_id, session_id),
                ).fetchone()
                if run is None:
                    raise ValueError(
                        f"Diagnostic run not found for QC session: {run_id}"
                    )
            connection.execute(
                """
                INSERT INTO evidence (
                    evidence_id, session_id, run_id, relative_path,
                    original_filename, media_type, size_bytes, sha256, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evidence_id,
                    session_id,
                    run_id,
                    relative_path,
                    original_filename,
                    media_type,
                    size_bytes,
                    sha256,
                    now,
                ),
            )
            self._append_audit(
                connection,
                "evidence",
                evidence_id,
                "created",
                (
                    _deserialize(session["identity_snapshot_json"])
                    if session["identity_snapshot_json"]
                    else {}
                ),
                metadata,
                now,
            )
            self._enqueue(
                connection,
                "evidence.created",
                "evidence",
                evidence_id,
                metadata,
                now,
                self.boot_session_id,
            )
        return metadata

    def get_evidence(self, evidence_id: str) -> dict[str, Any] | None:
        with self.connection() as connection:
            row = connection.execute(
                """
                SELECT evidence_id, session_id, run_id, relative_path,
                       original_filename, media_type, size_bytes, sha256, created_at
                FROM evidence WHERE evidence_id = ?
                """,
                (evidence_id,),
            ).fetchone()
        return dict(row) if row else None

    def list_evidence(self, session_id: str) -> list[dict[str, Any]]:
        with self.connection() as connection:
            rows = connection.execute(
                """
                SELECT evidence_id, session_id, run_id, original_filename,
                       media_type, size_bytes, sha256, created_at, sync_state
                FROM evidence WHERE session_id = ? ORDER BY created_at, evidence_id
                """,
                (session_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def create_storage_benchmark(
        self,
        benchmark_id: str,
        device_id: str,
        mountpoint: str,
        payload: dict[str, Any],
    ) -> None:
        started_at = str(payload["started_at"])
        session_id = payload.get("session_id")
        with self.connection() as connection:
            connection.execute(
                """
                INSERT INTO storage_benchmarks (
                    benchmark_id, device_id, mountpoint, status, started_at,
                    payload_json, session_id
                ) VALUES (?, ?, ?, 'Running', ?, ?, ?)
                """,
                (
                    benchmark_id,
                    device_id,
                    mountpoint,
                    started_at,
                    _serialize(payload),
                    session_id,
                ),
            )

    def finish_storage_benchmark(
        self,
        benchmark_id: str,
        status: str,
        payload: dict[str, Any],
    ) -> bool:
        if status not in {"Completed", "Interrupted", "Failed"}:
            raise ValueError(f"Invalid final benchmark status: {status}")
        completed_at = datetime.now(UTC).isoformat()
        with self.connection() as connection:
            row = connection.execute(
                """
                SELECT device_id FROM storage_benchmarks
                WHERE benchmark_id = ? AND status = 'Running'
                """,
                (benchmark_id,),
            ).fetchone()
            if row is None:
                return False
            connection.execute(
                """
                UPDATE storage_benchmarks
                SET status = ?, completed_at = ?, payload_json = ?
                WHERE benchmark_id = ?
                """,
                (status, completed_at, _serialize(payload), benchmark_id),
            )
            self._enqueue(
                connection,
                "storage_benchmark.completed",
                "storage_benchmark",
                benchmark_id,
                payload,
                completed_at,
                self.boot_session_id,
            )
        return True

    def get_storage_benchmark(self, benchmark_id: str) -> dict[str, Any] | None:
        with self.connection() as connection:
            row = connection.execute(
                """
                SELECT benchmark_id, device_id, mountpoint, status, started_at,
                       completed_at, payload_json, session_id
                FROM storage_benchmarks WHERE benchmark_id = ?
                """,
                (benchmark_id,),
            ).fetchone()
        if row is None:
            return None
        record = dict(row)
        record["data"] = json.loads(record.pop("payload_json"))
        return record

    def list_storage_benchmarks(
        self,
        device_id: str | None = None,
        limit: int = 100,
        session_id: str | None = None,
    ) -> list[dict[str, Any]]:
        with self.connection() as connection:
            filters = []
            values: list[Any] = []
            if device_id is not None:
                filters.append("device_id = ?")
                values.append(device_id)
            if session_id is not None:
                filters.append("session_id = ?")
                values.append(session_id)
            where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
            if where_clause:
                rows = connection.execute(
                    f"""
                    SELECT benchmark_id, device_id, mountpoint, status, started_at,
                           completed_at, payload_json, session_id
                    FROM storage_benchmarks {where_clause}
                    ORDER BY started_at DESC LIMIT ?
                    """,
                    (*values, max(1, min(limit, 500))),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT benchmark_id, device_id, mountpoint, status, started_at,
                           completed_at, payload_json, session_id
                    FROM storage_benchmarks
                    ORDER BY started_at DESC LIMIT ?
                    """,
                    (max(1, min(limit, 500)),),
                ).fetchall()
        records = []
        for row in rows:
            record = dict(row)
            record["data"] = json.loads(record.pop("payload_json"))
            records.append(record)
        return records

    def sync_status(self) -> dict[str, Any]:
        with self.connection() as connection:
            counts = {
                row["state"]: row["count"]
                for row in connection.execute(
                    "SELECT state, COUNT(*) AS count FROM outbox_events GROUP BY state"
                )
            }
            latest = connection.execute(
                "SELECT MAX(synced_at) AS last_sync FROM outbox_events"
            ).fetchone()
            failed = connection.execute(
                """
                SELECT event_id, event_type, entity_type, entity_id, attempts,
                       last_error, created_at
                FROM outbox_events
                WHERE state = 'Needs attention'
                ORDER BY created_at LIMIT 50
                """
            ).fetchall()
        return {
            "enabled": get_settings().STORAGE_BACKEND == "sqlite",
            "states": {
                state: int(counts.get(state, 0))
                for state in ("Pending", "Syncing", "Synced", "Needs attention")
            },
            "last_successful_sync": latest["last_sync"],
            "failed_events": [dict(row) for row in failed],
            "cloud_configured": bool(
                get_settings().CLOUD_API_URL and get_settings().CLOUD_STATION_TOKEN
            ),
        }

    def entity_sync_status(self, entity_type: str, entity_id: str) -> dict[str, Any]:
        with self.connection() as connection:
            row = connection.execute(
                """
                SELECT state, attempts, last_error, created_at, synced_at
                FROM outbox_events
                WHERE entity_type = ? AND entity_id = ?
                ORDER BY created_at DESC, event_id DESC LIMIT 1
                """,
                (entity_type, entity_id),
            ).fetchone()
        return {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "state": row["state"] if row else "Local only",
            "attempts": int(row["attempts"]) if row else 0,
            "last_error": row["last_error"] if row else None,
            "created_at": row["created_at"] if row else None,
            "synced_at": row["synced_at"] if row else None,
            "cloud_configured": bool(
                get_settings().CLOUD_API_URL
                and get_settings().CLOUD_STATION_TOKEN
            ),
        }

    def retry_sync(self, event_id: str | None = None) -> int:
        now = datetime.now(UTC).isoformat()
        with self.connection() as connection:
            if event_id is None:
                cursor = connection.execute(
                    """
                    UPDATE outbox_events
                    SET state = 'Pending', attempts = 0,
                        next_attempt_at = ?, last_error = NULL
                    WHERE state = 'Needs attention'
                    """,
                    (now,),
                )
            else:
                cursor = connection.execute(
                    """
                    UPDATE outbox_events
                    SET state = 'Pending', attempts = 0,
                        next_attempt_at = ?, last_error = NULL
                    WHERE event_id = ? AND state = 'Needs attention'
                    """,
                    (now, event_id),
                )
            return cursor.rowcount

    def claim_outbox(self, limit: int = 20) -> list[dict[str, Any]]:
        now = datetime.now(UTC).isoformat()
        with self.connection() as connection:
            rows = connection.execute(
                """
                SELECT event_id, event_type, entity_type, entity_id,
                       schema_version, created_at, payload_json, attempts,
                       boot_session_id
                FROM outbox_events
                WHERE state = 'Pending'
                  AND (next_attempt_at IS NULL OR next_attempt_at <= ?)
                ORDER BY created_at, event_id
                LIMIT ?
                """,
                (now, max(1, min(limit, 100))),
            ).fetchall()
            events = [dict(row) for row in rows]
            for event in events:
                connection.execute(
                    """
                    UPDATE outbox_events
                    SET state = 'Syncing', attempts = attempts + 1
                    WHERE event_id = ? AND state = 'Pending'
                    """,
                    (event["event_id"],),
                )
                event["payload"] = json.loads(event.pop("payload_json"))
                event["attempts"] += 1
        return events

    def recover_interrupted_sync(self) -> int:
        with self.connection() as connection:
            cursor = connection.execute(
                """
                UPDATE outbox_events
                SET state = 'Pending'
                WHERE state = 'Syncing'
                """
            )
            return cursor.rowcount

    def acknowledge_sync(self, event_id: str) -> bool:
        now = datetime.now(UTC).isoformat()
        with self.connection() as connection:
            cursor = connection.execute(
                """
                UPDATE outbox_events
                SET state = 'Synced', synced_at = ?, last_error = NULL
                WHERE event_id = ? AND state = 'Syncing'
                """,
                (now, event_id),
            )
            if cursor.rowcount == 1:
                event = connection.execute(
                    "SELECT entity_type, entity_id FROM outbox_events WHERE event_id = ?",
                    (event_id,),
                ).fetchone()
                if event and event["entity_type"] == "evidence":
                    connection.execute(
                        "UPDATE evidence SET sync_state = 'Synced' WHERE evidence_id = ?",
                        (event["entity_id"],),
                    )
            return cursor.rowcount == 1

    def fail_sync(
        self,
        event_id: str,
        error: str,
        *,
        max_attempts: int = 10,
    ) -> bool:
        now = datetime.now(UTC)
        with self.connection() as connection:
            row = connection.execute(
                """
                SELECT attempts, entity_type, entity_id FROM outbox_events
                WHERE event_id = ? AND state = 'Syncing'
                """,
                (event_id,),
            ).fetchone()
            if row is None:
                return False
            attempts = int(row["attempts"])
            state = "Needs attention" if attempts >= max_attempts else "Pending"
            delay_seconds = min(3600, 2 ** min(attempts, 12))
            next_attempt = (
                None
                if state == "Needs attention"
                else (now.timestamp() + delay_seconds)
            )
            next_attempt_at = (
                datetime.fromtimestamp(next_attempt, UTC).isoformat()
                if next_attempt is not None
                else None
            )
            connection.execute(
                """
                UPDATE outbox_events
                SET state = ?, next_attempt_at = ?, last_error = ?
                WHERE event_id = ?
                """,
                (state, next_attempt_at, error[:2000], event_id),
            )
            if state == "Needs attention":
                connection.execute(
                    """
                    UPDATE evidence SET sync_state = 'Needs attention'
                    WHERE evidence_id = ?
                    """,
                    (row["entity_id"] if row["entity_type"] == "evidence" else "",),
                )
            return True

    def _persist_session_devices(
        self,
        connection: sqlite3.Connection,
        payload: dict[str, Any],
        company_id: str | None,
        now: str,
    ) -> None:
        devices = payload.get("discovered_devices")
        if not isinstance(devices, list):
            return
        for device in devices:
            if not isinstance(device, dict):
                continue
            device_id = device.get("device_id")
            if not isinstance(device_id, str) or not device_id:
                continue
            connection.execute(
                """
                INSERT INTO devices (
                    device_id, company_id, payload_json, first_seen_at, updated_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(device_id) DO UPDATE SET
                    payload_json = excluded.payload_json,
                    updated_at = excluded.updated_at
                """,
                (
                    device_id,
                    company_id,
                    _serialize(device),
                    now,
                    now,
                ),
            )

    @staticmethod
    def _persist_session_asset(
        connection: sqlite3.Connection,
        session_id: str,
        asset_id: str,
        asset_payload: Any,
        created_at: str,
        now: str,
    ) -> None:
        asset = asset_payload if isinstance(asset_payload, dict) else {}
        payload_asset_id = asset.get("asset_id")
        if payload_asset_id is not None and payload_asset_id != asset_id:
            raise ValueError("The session asset payload does not match asset_id.")
        existing_asset = connection.execute(
            "SELECT payload_json FROM assets WHERE asset_id = ?",
            (asset_id,),
        ).fetchone()
        if existing_asset is not None:
            previous = _deserialize(existing_asset["payload_json"])
            asset = {
                **previous,
                **{
                    key: value
                    for key, value in asset.items()
                    if value is not None
                },
            }
        asset = {**asset, "asset_id": asset_id}
        connection.execute(
            """
            INSERT INTO assets (asset_id, payload_json, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(asset_id) DO UPDATE SET
                payload_json = excluded.payload_json,
                updated_at = excluded.updated_at
            """,
            (asset_id, _serialize(asset), created_at, now),
        )
        existing = connection.execute(
            "SELECT asset_id FROM session_asset_links WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        if existing is not None and existing["asset_id"] != asset_id:
            raise ValueError("A QC session cannot be reassigned to another asset.")
        connection.execute(
            """
            INSERT OR IGNORE INTO session_asset_links (session_id, asset_id)
            VALUES (?, ?)
            """,
            (session_id, asset_id),
        )

    @staticmethod
    def _persist_session_components(
        connection: sqlite3.Connection,
        asset_id: str,
        component_payloads: Any,
        now: str,
    ) -> None:
        if component_payloads is None:
            return
        if not isinstance(component_payloads, list):
            raise ValueError("Session components must be a list.")
        for component in component_payloads:
            if not isinstance(component, dict):
                raise ValueError("Session component entries must be objects.")
            component_id = component.get("component_id")
            component_asset_id = component.get("asset_id")
            category = component.get("category")
            identity_key = component.get("identity_key")
            if (
                not isinstance(component_id, str)
                or not component_id
                or not isinstance(category, str)
                or not category
                or not isinstance(identity_key, str)
                or not identity_key
            ):
                raise ValueError("Each component requires canonical identity fields.")
            if component_asset_id != asset_id:
                raise ValueError("A component must belong to its session asset.")
            existing = connection.execute(
                """
                SELECT component_id
                FROM hardware_components
                WHERE asset_id = ? AND identity_key = ?
                """,
                (asset_id, identity_key),
            ).fetchone()
            if existing is not None and existing["component_id"] != component_id:
                raise ValueError("A component identity key cannot change its ID.")
            existing_id = connection.execute(
                """
                SELECT asset_id, identity_key
                FROM hardware_components
                WHERE component_id = ?
                """,
                (component_id,),
            ).fetchone()
            if existing_id is not None and (
                existing_id["asset_id"] != asset_id
                or existing_id["identity_key"] != identity_key
            ):
                raise ValueError("A component ID cannot be reassigned.")
            connection.execute(
                """
                INSERT INTO hardware_components (
                    component_id, asset_id, category, identity_key,
                    legacy_device_id, identity_basis, payload_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(component_id) DO UPDATE SET
                    payload_json = excluded.payload_json,
                    updated_at = excluded.updated_at
                """,
                (
                    component_id,
                    asset_id,
                    category,
                    identity_key,
                    component.get("legacy_device_id"),
                    str(component.get("identity_basis") or "unknown"),
                    _serialize(component),
                    now,
                ),
            )

    @staticmethod
    def _persist_diagnostic_runs(
        connection: sqlite3.Connection,
        session_id: str,
        payload: dict[str, Any],
        now: str,
        asset_id: str | None,
    ) -> None:
        collection = payload.get("diagnostic_results")
        results = (
            collection.get("results")
            if isinstance(collection, dict)
            else getattr(collection, "results", None)
        )
        if not isinstance(results, list):
            return
        from app.persistence.session_serialization import json_value

        for result_item in results:
            result = (
                result_item
                if isinstance(result_item, dict)
                else json_value(result_item)
            )
            if not isinstance(result, dict):
                continue
            run_id = result.get("run_id")
            diagnostic_type = result.get("diagnostic_type")
            if (
                not isinstance(run_id, str)
                or not run_id
                or not isinstance(diagnostic_type, str)
            ):
                continue
            result_session_id = result.get("session_id")
            if result_session_id not in (None, session_id):
                raise ValueError(
                    "A diagnostic run must belong to its containing QC session."
                )
            created_at = result.get("created_at")
            if not isinstance(created_at, str):
                created_at = now
            status = result.get("status")
            if hasattr(status, "value"):
                status = status.value
            if not isinstance(status, str):
                status = str(status or "unknown")
            details = result.get("details")
            parent_run_id = (
                details.get("parent_run_id")
                if isinstance(details, dict)
                else None
            )
            existing_run = connection.execute(
                """
                SELECT session_id, payload_json
                FROM diagnostic_runs WHERE run_id = ?
                """,
                (run_id,),
            ).fetchone()
            if existing_run is not None and existing_run["session_id"] != session_id:
                raise sqlite3.IntegrityError(
                    "diagnostic run does not belong to the supplied session"
                )
            run_previously_persisted = existing_run is not None
            serialized_result = _serialize(result)
            if existing_run is None:
                connection.execute(
                    """
                    INSERT INTO diagnostic_runs (
                        run_id, session_id, parent_run_id, diagnostic_type, device_id,
                        status, created_at, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        session_id,
                        parent_run_id,
                        diagnostic_type,
                        result.get("device_id"),
                        status,
                        created_at,
                        serialized_result,
                    ),
                )
            else:
                previous_payload = json.loads(existing_run["payload_json"])
                current_payload = json.loads(serialized_result)
                previous_payload.pop("run_id", None)
                current_payload.pop("run_id", None)
                for key in list(current_payload):
                    if key not in previous_payload and current_payload[key] is None:
                        current_payload.pop(key)
                if (
                    previous_payload != current_payload
                ):
                    raise sqlite3.IntegrityError(
                        f"Diagnostic run_id cannot overwrite an existing execution: {run_id}"
                    )

            existing_result = connection.execute(
                """
                SELECT payload_json FROM diagnostic_results
                WHERE result_id = ?
                """,
                (run_id,),
            ).fetchone()
            if existing_result is None:
                connection.execute(
                    """
                    INSERT INTO diagnostic_results (
                        result_id, run_id, created_at, payload_json
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (run_id, run_id, created_at, serialized_result),
                )
            elif existing_result["payload_json"] != serialized_result:
                previous_result = json.loads(existing_result["payload_json"])
                current_result = json.loads(serialized_result)
                previous_result.pop("run_id", None)
                current_result.pop("run_id", None)
                for key in list(current_result):
                    if key not in previous_result and current_result[key] is None:
                        current_result.pop(key)
                if previous_result != current_result:
                    raise sqlite3.IntegrityError(
                        f"Diagnostic result cannot overwrite an existing execution: {run_id}"
                    )

            result_asset_id = result.get("asset_id")
            component_id = result.get("component_id")
            identity_asset_id = result_asset_id
            if (
                identity_asset_id is None
                and asset_id is not None
                and not run_previously_persisted
            ):
                identity_asset_id = asset_id
            if identity_asset_id is not None and identity_asset_id != asset_id:
                raise ValueError(
                    "A diagnostic run must use the asset assigned to its QC session."
                )
            if component_id is not None and asset_id is None:
                raise ValueError(
                    "A component-linked diagnostic run requires a session asset."
                )
            if identity_asset_id is not None and asset_id is not None:
                existing_identity = connection.execute(
                    """
                    SELECT session_id, asset_id, component_id
                    FROM diagnostic_run_identities
                    WHERE run_id = ?
                    """,
                    (run_id,),
                ).fetchone()
                expected_identity = (session_id, asset_id, component_id)
                if existing_identity is None:
                    connection.execute(
                        """
                        INSERT INTO diagnostic_run_identities (
                            run_id, session_id, asset_id, component_id
                        ) VALUES (?, ?, ?, ?)
                        """,
                        (run_id, session_id, asset_id, component_id),
                    )
                elif tuple(existing_identity) != expected_identity:
                    raise sqlite3.IntegrityError(
                        "A diagnostic run identity cannot be reassigned."
                    )

    @staticmethod
    def _append_audit(
        connection: sqlite3.Connection,
        entity_type: str,
        entity_id: str,
        event_type: str,
        actor: dict[str, Any],
        payload: dict[str, Any],
        created_at: str,
    ) -> None:
        connection.execute(
            """
            INSERT INTO audit_events (
                audit_event_id, entity_type, entity_id, event_type,
                actor_snapshot_json, payload_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                entity_type,
                entity_id,
                event_type,
                _serialize(actor),
                _serialize(payload),
                created_at,
            ),
        )

    @staticmethod
    def _enqueue(
        connection: sqlite3.Connection,
        event_type: str,
        entity_type: str,
        entity_id: str,
        payload: dict[str, Any],
        created_at: str,
        boot_session_id: str | None = None,
    ) -> None:
        connection.execute(
            """
            INSERT INTO outbox_events (
                event_id, event_type, entity_type, entity_id, schema_version,
                created_at, payload_json, state, boot_session_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'Pending', ?)
            """,
            (
                str(uuid.uuid4()),
                event_type,
                entity_type,
                entity_id,
                1,
                created_at,
                _serialize(payload),
                boot_session_id,
            ),
        )

    def _migrate(self) -> None:
        with self.connection() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )
                """
            )
            migration_dir = Path(__file__).parent / "migrations"
            for migration_path in sorted(migration_dir.glob("[0-9]*.sql")):
                applied = connection.execute(
                    "SELECT 1 FROM schema_migrations WHERE version = ?",
                    (migration_path.name,),
                ).fetchone()
                if applied:
                    continue
                script = migration_path.read_text(encoding="utf-8")
                connection.executescript(
                    "BEGIN IMMEDIATE;\n"
                    + script
                    + "\nINSERT INTO schema_migrations (version, applied_at) "
                    + "VALUES ("
                    + _sql_literal(migration_path.name)
                    + ", "
                    + _sql_literal(datetime.now(UTC).isoformat())
                    + ");\nCOMMIT;"
                )


def _serialize(value: Any) -> str:
    from app.persistence.session_serialization import json_value

    return json.dumps(json_value(value), ensure_ascii=False, separators=(",", ":"))


def _deserialize(value: str) -> dict[str, Any]:
    from app.persistence.session_serialization import restore_session

    payload = json.loads(value)
    if not isinstance(payload, dict):
        raise ValueError("Persisted record payload must be a JSON object.")
    return restore_session(payload)


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


_PROCESS_BOOT_SESSION_ID = str(uuid.uuid4())


def _current_boot_session_id() -> str:
    if sys.platform == "linux":
        try:
            return Path("/proc/sys/kernel/random/boot_id").read_text(
                encoding="ascii"
            ).strip()
        except OSError:
            pass
    return _PROCESS_BOOT_SESSION_ID


def _session_identity_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    intake = payload.get("intake_record")
    intake = intake if isinstance(intake, dict) else {}
    return {
        "asset_id": payload.get("asset_id"),
        "company_id": intake.get("company_id"),
        "company_name": intake.get("company_name"),
        "technician": intake.get("technician"),
        "station_id": intake.get("station_id"),
    }
