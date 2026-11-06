from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import sqlite3

import pytest

from app.core.config import get_settings
from app.discovery.models.device import Device
from app.domain.assets import Asset, HardwareComponent, components_from_discovery
from app.hal.diagnostic_result import DiagnosticResult
from app.hal.models.diagnostic_result_collection import DiagnosticResultCollection
from app.persistence.local.database import SQLiteDatabase
from app.persistence.local.import_legacy import import_legacy_files
from app.services.diagnostic_session_service import DiagnosticSessionService
from app.workflows.reporting.diagnostic_report import DiagnosticReport


def _session_payload(
    session_id: str,
    asset_id: str | None,
    *,
    components: list[dict] | None = None,
    run_id: str | None = None,
    run_asset_id: str | None = None,
    component_id: str | None = None,
    run_session_id: str | None = None,
) -> dict:
    payload = {
        "session_id": session_id,
        "created_at": datetime.now(UTC).isoformat(),
        "device_id": "cpu",
    }
    if asset_id is not None:
        payload.update(
            asset_id=asset_id,
            asset=Asset(asset_id=asset_id).to_dict(),
            components=components or [],
        )
    if run_id is not None:
        payload["diagnostic_results"] = {
            "results": [
                {
                    "diagnostic_id": run_id,
                    "run_id": run_id,
                    "diagnostic_type": "cpu",
                    "session_id": run_session_id,
                    "device_id": "cpu",
                    "status": "passed",
                    "created_at": datetime.now(UTC).isoformat(),
                    "asset_id": run_asset_id,
                    "component_id": component_id,
                    "details": {},
                }
            ]
        }
    return payload


def test_component_ids_are_stable_asset_scoped_and_allow_repeated_categories():
    memory = Device(
        device_id="memory",
        device_type="memory",
        name="System Memory",
        properties={
            "memory_modules": [
                {"serial_number": "RAM-A", "bank": "DIMM_A1", "capacity_bytes": 8},
                {"serial_number": "RAM-B", "bank": "DIMM_B1", "capacity_bytes": 8},
            ]
        },
    )

    first_scan = components_from_discovery("asset-1", [memory])
    repeated_scan = components_from_discovery("asset-1", [memory])
    other_asset_scan = components_from_discovery("asset-2", [memory])

    module_ids = [
        item.component_id for item in first_scan
        if item.category == "memory_module"
    ]
    assert len(module_ids) == 2
    assert len(set(module_ids)) == 2
    assert [item.component_id for item in repeated_scan] == [
        item.component_id for item in first_scan
    ]
    assert {
        item.component_id for item in other_asset_scan
    }.isdisjoint({item.component_id for item in first_scan})
    assert all(
        not item.provisional
        for item in first_scan
        if item.category == "memory_module"
    )


def test_duplicate_component_serials_use_distinct_reported_slots():
    device = Device(
        device_id="memory",
        device_type="memory",
        name="System Memory",
        properties={
            "memory_modules": [
                {"serial_number": "duplicate", "bank": "DIMM_A1"},
                {"serial_number": "duplicate", "bank": "DIMM_B1"},
            ]
        },
    )

    modules = [
        item for item in components_from_discovery("asset-1", [device])
        if item.category == "memory_module"
    ]

    assert len(modules) == 2
    assert modules[0].component_id != modules[1].component_id
    assert {item.identity_basis for item in modules} == {"slot"}
    assert all(item.provisional for item in modules)


def test_duplicate_storage_serials_do_not_merge_distinct_provider_devices():
    devices = [
        Device(
            device_id=f"storage:/dev/{suffix}",
            device_type="storage",
            name="Drive",
            properties={"serial_number": "duplicate"},
        )
        for suffix in ("sda", "sdb")
    ]

    components = components_from_discovery("asset-1", devices)

    assert len(components) == 2
    assert components[0].component_id != components[1].component_id
    assert {item.identity_basis for item in components} == {"provider_id"}
    assert all(item.provisional for item in components)


def test_missing_component_provider_ids_remain_distinct_and_provisional():
    devices = [
        Device(
            device_id="",
            device_type="storage",
            name="Drive",
            properties={"model": "same-model"},
        )
        for _ in range(2)
    ]

    components = components_from_discovery("asset-1", devices)

    assert len(components) == 2
    assert components[0].component_id != components[1].component_id
    assert all(item.identity_basis == "reported_index" for item in components)
    assert all(item.provisional for item in components)


def test_component_rediscovery_is_stable_and_serial_replacement_is_distinct():
    first_drive = Device(
        device_id="storage:/dev/sda",
        device_type="storage",
        name="Drive",
        properties={"serial_number": "drive-a"},
    )
    replacement_drive = Device(
        device_id="storage:/dev/sda",
        device_type="storage",
        name="Drive",
        properties={"serial_number": "drive-b"},
    )

    original = components_from_discovery("asset-1", [first_drive])[0]
    rediscovered = components_from_discovery("asset-1", [first_drive])[0]
    replacement = components_from_discovery("asset-1", [replacement_drive])[0]

    assert original.component_id == rediscovered.component_id
    assert not original.provisional
    assert replacement.component_id != original.component_id
    assert not replacement.provisional


def test_database_persists_session_asset_component_and_canonical_run(tmp_path):
    database = SQLiteDatabase(tmp_path / "identity.sqlite3")
    asset_id = "asset-a"
    component = HardwareComponent.create(
        asset_id=asset_id,
        category="cpu",
        identity_key="provider_id:cpu",
        legacy_device_id="cpu",
    )

    session_payload = _session_payload(
        "session-a",
        asset_id,
        components=[component.to_dict()],
    )
    session_payload["diagnostic_results"] = DiagnosticResultCollection(
        [
            DiagnosticResult(
                diagnostic_id="cpu",
                diagnostic_type="cpu",
                device_id="cpu",
                status="passed",
                run_id="run-a",
                asset_id=asset_id,
                component_id=component.component_id,
            )
        ]
    )
    database.save_session("session-a", session_payload, enqueue_sync=False)
    database.save_session("session-a", session_payload, enqueue_sync=False)
    database.save_session(
        "session-a2",
        _session_payload("session-a2", asset_id),
        enqueue_sync=False,
    )

    loaded = database.get_session("session-a")
    assert loaded is not None
    run = loaded["diagnostic_results"].results[0]
    assert run.run_id == "run-a"
    assert run.diagnostic_id == "cpu"
    assert run.asset_id == asset_id
    assert run.component_id == component.component_id
    assert loaded["asset_id"] == asset_id

    with database.connection() as connection:
        identity = connection.execute(
            """
            SELECT run_id, session_id, asset_id, component_id
            FROM diagnostic_run_identities
            WHERE run_id = 'run-a'
            """
        ).fetchone()
        assert tuple(identity) == (
            "run-a",
            "session-a",
            asset_id,
            component.component_id,
        )
        assert connection.execute(
            "SELECT count(*) FROM assets WHERE asset_id = ?",
            (asset_id,),
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT count(*) FROM hardware_components WHERE asset_id = ?",
            (asset_id,),
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT count(*) FROM session_asset_links WHERE asset_id = ?",
            (asset_id,),
        ).fetchone()[0] == 2

    evidence = database.save_evidence_metadata(
        evidence_id="evidence-a",
        session_id="session-a",
        run_id="run-a",
        relative_path="Boot_Sessions/test/file.png",
        original_filename="file.png",
        media_type="image/png",
        size_bytes=1,
        sha256="0" * 64,
    )
    assert evidence["evidence_id"] == "evidence-a"
    with pytest.raises(ValueError, match="not found for QC session"):
        database.save_evidence_metadata(
            evidence_id="evidence-wrong-owner",
            session_id="session-a2",
            run_id="run-a",
            relative_path="Boot_Sessions/test/wrong.png",
            original_filename="wrong.png",
            media_type="image/png",
            size_bytes=1,
            sha256="0" * 64,
        )
    with pytest.raises(
        sqlite3.IntegrityError,
        match="evidence run does not belong",
    ):
        with database.connection() as connection:
            connection.execute(
                """
                INSERT INTO evidence (
                    evidence_id, session_id, run_id, relative_path,
                    original_filename, media_type, size_bytes, sha256, created_at
                ) VALUES (
                    'evidence-db-wrong-owner', 'session-a2', 'run-a',
                    'Boot_Sessions/test/db-wrong.png', 'db-wrong.png',
                    'image/png', 1, ?, ?
                )
                """,
                ("0" * 64, datetime.now(UTC).isoformat()),
            )


def test_session_and_run_asset_ownership_are_enforced(tmp_path):
    database = SQLiteDatabase(tmp_path / "ownership.sqlite3")
    component = HardwareComponent.create(
        asset_id="asset-a",
        category="cpu",
        identity_key="provider_id:cpu",
    )
    database.save_session(
        "session-a",
        _session_payload(
            "session-a",
            "asset-a",
            components=[component.to_dict()],
            run_id="run-a",
            run_asset_id="asset-a",
            component_id=component.component_id,
        ),
        enqueue_sync=False,
    )

    with pytest.raises(ValueError, match="another asset"):
        database.save_session(
            "session-a",
            _session_payload("session-a", "asset-b"),
            enqueue_sync=False,
        )

    with pytest.raises(ValueError, match="assigned to its QC session"):
        database.save_session(
            "session-b",
            _session_payload(
                "session-b",
                "asset-b",
                run_id="run-b",
                run_asset_id="asset-a",
            ),
            enqueue_sync=False,
        )

    with pytest.raises(ValueError, match="containing QC session"):
        database.save_session(
            "session-d",
            _session_payload(
                "session-d",
                "asset-b",
                run_id="run-d",
                run_asset_id="asset-b",
                run_session_id="session-a",
            ),
            enqueue_sync=False,
        )

    with pytest.raises(sqlite3.IntegrityError, match="ownership cannot be changed"):
        with database.connection() as connection:
            connection.execute(
                """
                UPDATE diagnostic_runs SET session_id = 'session-b'
                WHERE run_id = 'run-a'
                """
            )
    with pytest.raises(
        sqlite3.IntegrityError,
        match="QC session asset ownership cannot be changed",
    ):
        with database.connection() as connection:
            connection.execute(
                """
                UPDATE session_asset_links SET asset_id = 'asset-b'
                WHERE session_id = 'session-a'
                """
            )

    with pytest.raises(ValueError, match="belong to its session asset"):
        database.save_session(
            "session-c",
            _session_payload(
                "session-c",
                "asset-b",
                components=[component.to_dict()],
            ),
            enqueue_sync=False,
        )


def test_database_rejects_a_run_reassigned_to_a_different_session(tmp_path):
    database = SQLiteDatabase(tmp_path / "run-owner.sqlite3")
    database.save_session(
        "session-a",
        _session_payload("session-a", "asset-a", run_id="shared-run"),
        enqueue_sync=False,
    )

    with pytest.raises(sqlite3.IntegrityError, match="does not belong"):
        database.save_session(
            "session-b",
            _session_payload("session-b", "asset-a", run_id="shared-run"),
            enqueue_sync=False,
        )


def test_legacy_sessions_without_canonical_ids_round_trip_unchanged(tmp_path):
    path = tmp_path / "legacy.sqlite3"
    database = SQLiteDatabase(path)
    legacy = _session_payload("legacy-session", None, run_id="legacy-run")
    legacy["diagnostic_results"]["results"][0].pop("run_id")
    legacy["diagnostic_results"]["results"][0]["diagnostic_id"] = "cpu"
    legacy["diagnostic_results"]["results"][0].pop("asset_id")
    legacy["diagnostic_results"]["results"][0].pop("component_id")

    database.save_session("legacy-session", legacy, enqueue_sync=False)
    reopened = SQLiteDatabase(path)
    loaded = reopened.get_session("legacy-session")

    assert loaded is not None
    assert loaded["device_id"] == "cpu"
    assert loaded.get("asset_id") is None
    legacy_result = loaded["diagnostic_results"].results[0]
    assert legacy_result.run_id is None
    assert legacy_result.diagnostic_id == "cpu"
    with reopened.connection() as connection:
        assert connection.execute(
            "SELECT count(*) FROM diagnostic_run_identities"
        ).fetchone()[0] == 0


def test_legacy_session_keeps_identity_unresolved_for_new_runs(tmp_path):
    database = SQLiteDatabase(tmp_path / "legacy-execution.sqlite3")
    legacy_payload = _session_payload(
        "legacy-session",
        None,
        run_id="legacy-run",
    )
    legacy_payload["diagnostic_results"]["results"][0].pop("run_id")
    legacy_payload["diagnostic_results"]["results"][0]["diagnostic_id"] = "cpu"
    database.save_session(
        "legacy-session",
        legacy_payload,
        enqueue_sync=False,
    )
    session = database.get_session("legacy-session")
    assert session is not None
    legacy_run = session["diagnostic_results"].results[0]

    assert legacy_run.run_id is None
    assert session.get("asset_id") is None

    session["diagnostic_results"] = DiagnosticResultCollection(
        [
            legacy_run,
            DiagnosticResult(
                diagnostic_id="cpu",
                diagnostic_type="cpu",
                device_id="cpu",
                status="passed",
                session_id="legacy-session",
            ),
        ]
    )
    database.save_session("legacy-session", session, enqueue_sync=False)

    with database.connection() as connection:
        identities = connection.execute(
            """
            SELECT run_id, session_id, asset_id
            FROM diagnostic_run_identities
            """
        ).fetchall()
        runs = connection.execute(
            "SELECT run_id, payload_json FROM diagnostic_runs ORDER BY run_id"
        ).fetchall()
    assert identities == []
    assert len(runs) == 1
    assert runs[0]["run_id"] == session["diagnostic_results"].results[1].run_id
    assert runs[0]["run_id"] != "cpu"


def test_reusing_run_id_cannot_overwrite_historical_execution(tmp_path):
    database = SQLiteDatabase(tmp_path / "immutable-runs.sqlite3")
    asset_id = "asset-a"
    original = DiagnosticResult(
        diagnostic_id="cpu",
        diagnostic_type="cpu",
        device_id="cpu",
        status="passed",
        run_id="run-fixed",
        asset_id=asset_id,
        details={"measurement": 1},
    )
    payload = _session_payload("session-a", asset_id)
    payload["diagnostic_results"] = DiagnosticResultCollection([original])
    database.save_session("session-a", payload, enqueue_sync=False)

    changed = DiagnosticResult(
        diagnostic_id="cpu",
        diagnostic_type="cpu",
        device_id="cpu",
        status="failed",
        run_id="run-fixed",
        asset_id=asset_id,
        details={"measurement": 2},
    )
    payload["diagnostic_results"] = DiagnosticResultCollection([changed])
    with pytest.raises(sqlite3.IntegrityError, match="cannot overwrite"):
        database.save_session("session-a", payload, enqueue_sync=False)

    with database.connection() as connection:
        stored = connection.execute(
            "SELECT payload_json FROM diagnostic_runs WHERE run_id = 'run-fixed'"
        ).fetchone()
    assert '"measurement":1' in stored["payload_json"]


def test_additive_migration_preserves_preexisting_session_and_run_rows(tmp_path):
    path = tmp_path / "pre-identity.sqlite3"
    connection = sqlite3.connect(path)
    connection.execute(
        """
        CREATE TABLE schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL
        )
        """
    )
    migration_dir = (
        Path(__file__).resolve().parents[2]
        / "app"
        / "persistence"
        / "local"
        / "migrations"
    )
    for migration in sorted(migration_dir.glob("[0-9]*.sql")):
        if migration.name.startswith("0006_"):
            continue
        escaped_name = migration.name.replace("'", "''")
        connection.executescript(
            "BEGIN IMMEDIATE;\n"
            + migration.read_text(encoding="utf-8")
            + "\nINSERT INTO schema_migrations (version, applied_at) VALUES ('"
            + escaped_name
            + "', '2026-01-01T00:00:00+00:00');\nCOMMIT;"
        )
    connection.execute(
        """
        INSERT INTO boot_sessions (
            boot_session_id, started_at, software_version, schema_version
        ) VALUES ('old-boot', '2026-01-01T00:00:00+00:00', 'old', 5)
        """
    )
    connection.execute(
        """
        INSERT INTO sessions (
            session_id, payload_json, created_at, updated_at, deleted_at
        ) VALUES (
            'historic-session',
            '{"session_id":"historic-session","device_id":"cpu"}',
            '2026-01-01T00:00:00+00:00',
            '2026-01-01T00:00:00+00:00',
            NULL
        )
        """
    )
    connection.execute(
        """
        INSERT INTO qc_sessions (
            session_id, boot_session_id, device_id, company_id, station_id,
            identity_snapshot_json, software_version, catalogue_version,
            schema_version, created_at, updated_at
        ) VALUES (
            'historic-session', 'old-boot', 'cpu', NULL, NULL, '{}',
            'old', NULL, 5, '2026-01-01T00:00:00+00:00',
            '2026-01-01T00:00:00+00:00'
        )
        """
    )
    connection.execute(
        """
        INSERT INTO diagnostic_runs (
            run_id, session_id, parent_run_id, diagnostic_type, device_id,
            status, created_at, payload_json
        ) VALUES (
            'historic-run', 'historic-session', NULL, 'cpu', 'cpu', 'passed',
            '2026-01-01T00:00:00+00:00',
            '{"diagnostic_id":"historic-run","diagnostic_type":"cpu"}'
        )
        """
    )
    connection.execute(
        """
        INSERT INTO diagnostic_results (
            result_id, run_id, created_at, payload_json
        ) VALUES (
            'historic-result', 'historic-run', '2026-01-01T00:00:00+00:00',
            '{"result_id":"historic-result"}'
        )
        """
    )
    connection.execute(
        """
        INSERT INTO evidence (
            evidence_id, session_id, run_id, relative_path, original_filename,
            media_type, size_bytes, sha256, created_at
        ) VALUES (
            'historic-evidence', 'historic-session', 'historic-run',
            'Boot_Sessions/historic/file.png', 'file.png', 'image/png', 1,
            '0000000000000000000000000000000000000000000000000000000000000000',
            '2026-01-01T00:00:00+00:00'
        )
        """
    )
    connection.execute(
        """
        INSERT INTO reports (
            report_id, payload_json, payload_html, created_at, updated_at, deleted_at
        ) VALUES (
            'historic-report', '{"report_id":"historic-report"}', '<p>old</p>',
            '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00', NULL
        )
        """
    )
    connection.execute(
        """
        INSERT INTO report_revisions (
            revision_id, report_id, revision, created_at, payload_json, payload_html
        ) VALUES (
            'historic-revision', 'historic-report', 1,
            '2026-01-01T00:00:00+00:00',
            '{"report_id":"historic-report","revision":1}', '<p>old</p>'
        )
        """
    )
    connection.commit()
    connection.close()

    migrated = SQLiteDatabase(path)

    with migrated.connection() as connection:
        assert connection.execute(
            "SELECT payload_json FROM sessions WHERE session_id = 'historic-session'"
        ).fetchone()[0] == (
            '{"session_id":"historic-session","device_id":"cpu"}'
        )
        assert connection.execute(
            "SELECT session_id FROM diagnostic_runs WHERE run_id = 'historic-run'"
        ).fetchone()[0] == "historic-session"
        assert connection.execute(
            "SELECT payload_json FROM diagnostic_results WHERE result_id = 'historic-result'"
        ).fetchone()[0] == '{"result_id":"historic-result"}'
        assert connection.execute(
            "SELECT run_id FROM evidence WHERE evidence_id = 'historic-evidence'"
        ).fetchone()[0] == "historic-run"
        assert connection.execute(
            "SELECT payload_json FROM reports WHERE report_id = 'historic-report'"
        ).fetchone()[0] == '{"report_id":"historic-report"}'
        assert connection.execute(
            """
            SELECT revision_id FROM report_revisions
            WHERE revision_id = 'historic-revision'
            """
        ).fetchone()[0] == "historic-revision"
        assert connection.execute(
            "SELECT count(*) FROM session_asset_links"
        ).fetchone()[0] == 0
        assert connection.execute(
            "SELECT count(*) FROM diagnostic_run_identities"
        ).fetchone()[0] == 0

    reopened = SQLiteDatabase(path)
    with reopened.connection() as connection:
        assert connection.execute(
            """
            SELECT count(*) FROM schema_migrations
            WHERE version = '0006_asset_component_identity.sql'
            """
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT count(*) FROM evidence WHERE evidence_id = 'historic-evidence'"
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT count(*) FROM report_revisions WHERE revision_id = 'historic-revision'"
        ).fetchone()[0] == 1


def test_asset_identity_migration_applies_to_fresh_database_and_repeats_safely(
    tmp_path,
):
    path = tmp_path / "fresh-identity.sqlite3"

    first = SQLiteDatabase(path)
    with first.connection() as connection:
        tables = {
            row["name"]
            for row in connection.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type = 'table'
                """
            )
        }
        assert {
            "assets",
            "hardware_components",
            "session_asset_links",
            "diagnostic_run_identities",
        } <= tables
        assert connection.execute(
            """
            SELECT count(*) FROM schema_migrations
            WHERE version = '0006_asset_component_identity.sql'
            """
        ).fetchone()[0] == 1

    second = SQLiteDatabase(path)
    with second.connection() as connection:
        assert connection.execute(
            """
            SELECT count(*) FROM schema_migrations
            WHERE version = '0006_asset_component_identity.sql'
            """
        ).fetchone()[0] == 1


def test_report_and_revision_ids_remain_distinct_and_report_identity_is_stable(tmp_path):
    database = SQLiteDatabase(tmp_path / "reports.sqlite3")
    session = {"session_id": "session-a", "asset_id": "asset-a"}
    first = DiagnosticReport()
    DiagnosticSessionService._set_report_identity(session, first)
    report_id = first.report_id
    first_revision_id = first.revision_id

    second = DiagnosticReport()
    DiagnosticSessionService._set_report_identity(session, second)
    assert second.report_id == report_id
    assert second.revision_id != first_revision_id
    assert second.report_id != second.revision_id
    assert second.session_id == "session-a"
    assert second.asset_id == "asset-a"

    database.save_report(
        report_id,
        {
            "report_id": report_id,
            "revision_id": second.revision_id,
            "session_id": second.session_id,
            "asset_id": second.asset_id,
        },
        None,
        enqueue_sync=False,
    )
    database.save_report(
        report_id,
        {
            "report_id": report_id,
            "revision_id": "another-revision",
            "session_id": second.session_id,
            "asset_id": second.asset_id,
        },
        None,
        enqueue_sync=False,
    )
    with database.connection() as connection:
        revisions = connection.execute(
            """
            SELECT revision_id
            FROM report_revisions
            WHERE report_id = ?
            ORDER BY revision
            """,
            (report_id,),
        ).fetchall()
    assert len(revisions) == 2
    assert revisions[0]["revision_id"] != revisions[1]["revision_id"]


def test_finalized_report_revision_is_immutable_and_requires_explicit_supersession(
    tmp_path,
):
    database = SQLiteDatabase(tmp_path / "finalized-report.sqlite3")
    report_key = "diagnostic-session-a"
    report_id = "stable-report-id"
    first_revision_id = "revision-one"
    first_payload = {
        "report_id": report_id,
        "revision_id": first_revision_id,
        "session_id": "session-a",
        "status": "passed",
        "data": {"result": "original"},
    }
    database.save_report(
        report_key,
        first_payload,
        "<p>original</p>",
        enqueue_sync=False,
    )
    finalized = database.finalize_report(
        report_key,
        first_revision_id,
        "QA",
    )
    assert finalized["finalized_at"]

    with pytest.raises(ValueError, match="already exists"):
        database.save_report(
            report_key,
            {**first_payload, "data": {"result": "changed"}},
            "<p>changed</p>",
            enqueue_sync=False,
        )
    with pytest.raises(sqlite3.IntegrityError, match="report revisions are immutable"):
        with database.connection() as connection:
            connection.execute(
                """
                UPDATE report_revisions SET payload_json = '{}'
                WHERE revision_id = ?
                """,
                (first_revision_id,),
            )

    second_revision_id = "revision-two"
    database.save_report(
        report_key,
        {
            **first_payload,
            "revision_id": second_revision_id,
            "supersedes_revision_id": first_revision_id,
            "supersession_reason": "Documented QC correction",
            "superseded_by": "QA",
            "data": {"result": "corrected"},
        },
        "<p>corrected</p>",
        enqueue_sync=False,
    )

    history = database.list_report_revisions(report_key)
    assert [item["revision_id"] for item in history] == [
        first_revision_id,
        second_revision_id,
    ]
    assert history[0]["report_id"] == history[1]["report_id"] == report_id
    assert history[0]["finalized_at"] == finalized["finalized_at"]
    assert history[1]["supersedes_revision_id"] == first_revision_id
    assert history[1]["supersession_reason"] == "Documented QC correction"


def test_live_sqlite_storage_imports_legacy_records_and_resolves_assets(
    monkeypatch,
    tmp_path,
):
    data_directory = tmp_path / "persistent-data"
    sessions_directory = data_directory / "sessions"
    reports_directory = data_directory / "reports"
    sessions_directory.mkdir(parents=True)
    reports_directory.mkdir()
    legacy_session = {
        "session_id": "legacy-unresolved",
        "device_id": "system",
        "status": "checks_complete",
    }
    legacy_report = {
        "report_id": "legacy-report",
        "revision_id": "legacy-revision",
        "session_id": "legacy-unresolved",
        "status": "checks_complete",
    }
    legacy_session_path = sessions_directory / "legacy-unresolved.json"
    legacy_report_path = reports_directory / "legacy-report.json"
    legacy_session_path.write_text(json.dumps(legacy_session), encoding="utf-8")
    legacy_report_path.write_text(json.dumps(legacy_report), encoding="utf-8")
    original_session_bytes = legacy_session_path.read_bytes()
    original_report_bytes = legacy_report_path.read_bytes()

    monkeypatch.setenv("DATA_DIR", str(data_directory))
    monkeypatch.setenv("SESSIONS_DIRECTORY", str(sessions_directory))
    monkeypatch.setenv("REPORTS_DIRECTORY", str(reports_directory))
    monkeypatch.setenv("SQLITE_DATABASE_PATH", str(data_directory / "uhdp.sqlite3"))
    monkeypatch.setenv("STORAGE_BACKEND", "sqlite")
    get_settings.cache_clear()
    try:
        database = SQLiteDatabase()
        imported = import_legacy_files(
            database,
            sessions_directory,
            [reports_directory],
        )
        service = DiagnosticSessionService()

        created = service.create_session(intake_record={"create_asset": True})
        linked = service.create_session(
            intake_record={"asset_id": created["asset_id"]}
        )
        unresolved = service.create_session()
        retest = service.create_session(
            intake_record={"retest_of_session_id": created["session_id"]}
        )
        legacy_retest = service.create_session(
            intake_record={"retest_of_session_id": "legacy-unresolved"}
        )

        assert imported == {"sessions": 1, "reports": 1, "skipped": 0}
        assert database.get_session("legacy-unresolved") is not None
        assert database.get_report_json("legacy-report")["revision_id"] == (
            "legacy-revision"
        )
        assert linked["asset_id"] == created["asset_id"]
        assert retest["asset_id"] == created["asset_id"]
        assert unresolved["asset_id"] is None
        assert legacy_retest["asset_id"] is None
        assert legacy_session_path.read_bytes() == original_session_bytes
        assert legacy_report_path.read_bytes() == original_report_bytes
    finally:
        get_settings.cache_clear()
