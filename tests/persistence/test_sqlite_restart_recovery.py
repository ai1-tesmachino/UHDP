from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
import hashlib
import json
import sqlite3
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.api import reports as reports_api
from app.discovery.models.device import Device
from app.hal.diagnostic_result import DiagnosticResult
from app.main import app
from app.persistence.local import database as database_module
from app.persistence.local.database import SQLiteDatabase
from app.persistence.local.import_legacy import import_legacy_files
from app.persistence.local.repositories import (
    SQLiteReportRepository,
    SQLiteSessionRepository,
    SQLiteReportStorage,
)
from app.persistence.session_serialization import json_value
from app.reports.report_generator import ReportGenerator
from app.services.diagnostic_session_service import DiagnosticSessionService
from app.workflows.templates.full_system_validation_workflow import (
    create_full_system_validation_workflow,
)


@pytest.fixture
def sqlite_settings(monkeypatch, tmp_path):
    data_directory = tmp_path / "data"
    monkeypatch.setenv("DATA_DIR", str(data_directory))
    monkeypatch.setenv("SQLITE_DATABASE_PATH", str(data_directory / "uhdp.sqlite3"))
    monkeypatch.setenv("STORAGE_BACKEND", "sqlite")
    monkeypatch.setenv("REPORTS_DIRECTORY", str(data_directory / "reports"))
    monkeypatch.setenv("SESSIONS_DIRECTORY", str(data_directory / "sessions"))
    get_settings.cache_clear()
    yield data_directory
    get_settings.cache_clear()


class FixtureDiscovery:
    def __init__(self) -> None:
        self.devices = [
            Device(
                device_id="system",
                device_type="system",
                name="System",
                properties={
                    "manufacturer": "Acme",
                    "model": "Model-X",
                    "serial_number": "SERIAL-123",
                    "processor": "Example CPU",
                    "ram": "16 GB",
                    "storage": "512 GB",
                    "display": "Panel-A",
                },
            ),
            Device(
                device_id="cpu",
                device_type="cpu",
                name="CPU",
                properties={"processor": "Example CPU", "logical_cores": 8},
            ),
            Device(
                device_id="memory",
                device_type="memory",
                name="Memory",
                properties={"total_ram_mb": 16384},
            ),
            Device(
                device_id="storage",
                device_type="storage",
                name="Storage",
                properties={"device": "/dev/example"},
            ),
            Device(
                device_id="display",
                device_type="display",
                name="Display",
                properties={"model": "Panel-A"},
            ),
        ]

    def discover(self):
        return SimpleNamespace(devices=self.devices)

    def get_device(self, device_id):
        return next(
            (device for device in self.devices if device.device_id == device_id),
            None,
        )


def test_sqlite_session_asset_result_report_survive_application_restart(
    sqlite_settings,
    monkeypatch,
):
    from app.services import diagnostic_session_service as session_module

    database_path = sqlite_settings / "uhdp.sqlite3"
    database = SQLiteDatabase(database_path)
    service = DiagnosticSessionService()
    service._repository = SQLiteSessionRepository(database)
    service._sessions = {}
    monkeypatch.setattr(session_module, "discovery_service", FixtureDiscovery())

    session_id = str(uuid4())
    initial = service.create_session(
        device_id="cpu",
        session_id=session_id,
        intake_record={
            "create_asset": True,
            "asset_tag": "ASSET-42",
            "technician": "Tech A",
            "planned_diagnostics": ["cpu"],
            "customer_reference": "WO-42",
        },
    )
    replay = service.create_session(
        device_id="cpu",
        session_id=session_id,
        intake_record={
            "create_asset": True,
            "asset_tag": "ASSET-42",
            "technician": "Tech A",
            "planned_diagnostics": ["cpu"],
            "customer_reference": "WO-42",
        },
    )
    assert replay["asset_id"] == initial["asset_id"]

    service.update_session_intake(
        session_id,
        device_id="cpu",
        intake_record={
            "technician": "Tech A",
            "planned_diagnostics": ["cpu"],
            "customer_reference": "WO-42",
        },
        device_inventory=[{"device_id": "cpu", "category": "cpu"}],
    )
    execution = service.execute_diagnostic(
        session_id=session_id,
        device_id="cpu",
        diagnostic_type="cpu",
    )
    returned_result = execution["result"]
    assert returned_result.evaluation is not None
    assert returned_result.evaluation.status.value == "inconclusive"
    assert returned_result.session_id == session_id
    assert returned_result.asset_id == initial["asset_id"]

    service.update_technician_record(
        session_id,
        {
            "fault_code": "THERMAL-01",
            "observed_issue": "Intermittent shutdown",
            "repair_performed": "Cleaned cooling assembly",
            "qa_approver": "QA A",
        },
    )
    service.update_technician_record(
        session_id,
        {
            "final_disposition": "Resale with disclosed issues",
            "final_disposition_reason": "Documented thermal concern",
        },
    )
    assert service.complete_session(session_id)["status"] == "checks_complete"
    assert service.finalize_session(session_id)["status"] == "completed"

    asset_id = initial["asset_id"]
    assert asset_id
    asset = database.get_asset(asset_id)
    assert asset is not None
    assert asset["asset_tag"] == "ASSET-42"
    assert asset["manufacturer"] == "Acme"
    assert asset["model"] == "Model-X"
    assert asset["serial_number"] == "SERIAL-123"
    assert asset["created_at"]
    assert asset["updated_at"]

    with database.connection() as connection:
        component_rows = connection.execute(
            """
            SELECT category, payload_json FROM hardware_components
            WHERE asset_id = ?
            """,
            (asset_id,),
        ).fetchall()
    components = {
        row["category"]: json.loads(row["payload_json"])
        for row in component_rows
    }
    assert {"cpu", "memory", "storage", "display"} <= set(components)
    assert components["cpu"]["properties"]["processor"] == "Example CPU"

    with database.connection() as connection:
        raw_result = json.loads(
            connection.execute(
                "SELECT payload_json FROM diagnostic_results WHERE result_id = ?",
                (returned_result.run_id,),
            ).fetchone()["payload_json"]
        )
    assert raw_result == json_value(returned_result)

    monkeypatch.setattr(
        database_module,
        "_current_boot_session_id",
        lambda: "boot-after-restart",
    )
    reopened_database = SQLiteDatabase.open_existing(database_path)
    restored_service = DiagnosticSessionService()
    restored_service._repository = SQLiteSessionRepository(reopened_database)
    restored_service._sessions = {}
    restored = restored_service.get_session(session_id)

    assert restored is not None
    assert restored["status"] == "completed"
    assert restored["asset_id"] == asset_id
    assert restored["intake_record"]["customer_reference"] == "WO-42"
    assert restored["technician_record"]["qa_approver"] == "QA A"
    assert (
        restored["technician_record"]["final_disposition"]
        == "Resale with disclosed issues"
    )
    persisted_result = restored["diagnostic_results"].results[0]
    assert json_value(persisted_result) == json_value(returned_result)

    report_repository = SQLiteReportRepository(reopened_database)
    report_name = f"diagnostic_{session_id}"
    report_json = report_repository.get_json(report_name)
    report_html = report_repository.get_html(report_name)
    assert report_json is not None
    assert report_html is not None
    assert report_json["report_id"] == restored["report_id"]
    assert report_json["session_id"] == session_id
    assert report_json["asset_id"] == asset_id
    assert report_json["data"]["asset"]["manufacturer"] == "Acme"
    assert report_json["data"]["technician_record"]["final_disposition"] == (
        "Resale with disclosed issues"
    )
    assert (
        report_json["data"]["cpu_result"]["evaluation"]["status"]
        == "inconclusive"
    )
    assert "SERIAL-123" in report_html
    assert "Resale with disclosed issues" in report_html
    assert "inconclusive" in report_html
    revisions = report_repository.list_revisions(report_name)
    assert revisions[-1]["finalized_at"]

    with reopened_database.connection() as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute(
            "SELECT count(*) FROM audit_events WHERE entity_id = ?",
            (session_id,),
        ).fetchone()[0] > 0
        assert connection.execute(
            "SELECT count(*) FROM boot_sessions WHERE boot_session_id = ?",
            ("boot-after-restart",),
        ).fetchone()[0] == 1


def test_api_diagnostic_session_and_reports_recover_after_sqlite_restart(
    sqlite_settings,
    monkeypatch,
):
    from app.services import diagnostic_session_service as session_module

    database_path = sqlite_settings / "uhdp.sqlite3"
    database = SQLiteDatabase(database_path)
    session_service = session_module.diagnostic_session_service
    session_repository = SQLiteSessionRepository(database)
    report_repository = SQLiteReportRepository(database)
    monkeypatch.setattr(session_service, "_repository", session_repository)
    monkeypatch.setattr(session_service, "_sessions", {})
    monkeypatch.setattr(session_module, "discovery_service", FixtureDiscovery())
    monkeypatch.setattr(reports_api, "session_repository", session_repository)
    monkeypatch.setattr(reports_api, "report_repository", report_repository)

    with TestClient(app) as client:
        created = client.post(
            "/diagnostic-sessions/",
            json={
                "device_id": "cpu",
                "create_asset": True,
                "asset_tag": "API-ASSET",
                "technician": "API Tech",
                "planned_diagnostics": ["cpu"],
            },
        )
        assert created.status_code == 200
        session_id = created.json()["session_id"]
        asset_id = created.json()["asset_id"]

        executed = client.post(
            f"/diagnostic-sessions/{session_id}/diagnostics/cpu/cpu"
        )
        assert executed.status_code == 200
        response_result = executed.json()
        assert response_result["session_id"] == session_id
        assert response_result["asset_id"] == asset_id
        assert response_result["status"] == "inconclusive"
        assert response_result["evaluation"]["status"] == "inconclusive"

        technician = client.put(
            f"/diagnostic-sessions/{session_id}/technician-record",
            json={
                "qa_approver": "API QA",
                "final_disposition": "Resale with disclosed issues",
                "final_disposition_reason": "Documented for follow-up",
            },
        )
        assert technician.status_code == 200
        assert client.post(
            f"/diagnostic-sessions/{session_id}/complete"
        ).json()["status"] == "checks_complete"
        assert client.post(
            f"/diagnostic-sessions/{session_id}/finalize"
        ).json()["status"] == "completed"
        report_response = client.get(f"/reports/{session_id}/json")
        assert report_response.status_code == 200
        original_report = report_response.json()

    monkeypatch.setattr(
        database_module,
        "_current_boot_session_id",
        lambda: "boot-api-restart",
    )
    reopened_database = SQLiteDatabase.open_existing(database_path)
    reopened_session_repository = SQLiteSessionRepository(reopened_database)
    reopened_report_repository = SQLiteReportRepository(reopened_database)
    monkeypatch.setattr(session_service, "_repository", reopened_session_repository)
    monkeypatch.setattr(session_service, "_sessions", {})
    monkeypatch.setattr(
        reports_api,
        "session_repository",
        reopened_session_repository,
    )
    monkeypatch.setattr(
        reports_api,
        "report_repository",
        reopened_report_repository,
    )

    with TestClient(app) as client:
        recovered_session = client.get(
            f"/diagnostic-sessions/{session_id}/report"
        )
        recovered_report = client.get(f"/reports/{session_id}/json")

    assert recovered_session.status_code == 200
    assert recovered_report.status_code == 200
    report_json = recovered_report.json()
    assert report_json == original_report
    assert report_json["asset_id"] == asset_id
    assert report_json["data"]["cpu_result"]["evaluation"]["status"] == (
        "inconclusive"
    )
    assert report_json["data"]["technician_record"]["qa_approver"] == "API QA"
    assert (
        report_json["data"]["technician_record"]["final_disposition"]
        == "Resale with disclosed issues"
    )


def test_sqlite_failed_session_write_rolls_back_all_related_records(tmp_path):
    database = SQLiteDatabase(tmp_path / "rollback.sqlite3")
    payload = {
        "session_id": "bad-session",
        "created_at": datetime.now(UTC).isoformat(),
        "asset_id": "asset-canonical",
        "asset": {"asset_id": "different-asset"},
    }

    with pytest.raises(ValueError, match="does not match asset_id"):
        database.save_session("bad-session", payload, enqueue_sync=False)

    with database.connection() as connection:
        assert connection.execute(
            "SELECT count(*) FROM sessions WHERE session_id = 'bad-session'"
        ).fetchone()[0] == 0
        assert connection.execute(
            "SELECT count(*) FROM qc_sessions WHERE session_id = 'bad-session'"
        ).fetchone()[0] == 0
        assert connection.execute(
            "SELECT count(*) FROM assets WHERE asset_id = 'asset-canonical'"
        ).fetchone()[0] == 0
        assert connection.execute(
            "SELECT count(*) FROM audit_events WHERE entity_id = 'bad-session'"
        ).fetchone()[0] == 0


def test_incomplete_workflow_report_does_not_mark_session_complete(
    sqlite_settings,
    monkeypatch,
):
    from app.services import diagnostic_session_service as session_module

    database = SQLiteDatabase(sqlite_settings / "uhdp.sqlite3")
    service = DiagnosticSessionService()
    service._repository = SQLiteSessionRepository(database)
    service._sessions = {}
    monkeypatch.setattr(session_module, "discovery_service", FixtureDiscovery())

    session = service.create_session(
        device_id="system",
        intake_record={
            "create_asset": True,
            "planned_diagnostics": ["cpu", "memory"],
            "technician": "Tech B",
        },
    )
    session["selected_diagnostics"] = ["cpu", "memory"]
    execution = service.execute_workflow(
        session_id=session["session_id"],
        workflow=create_full_system_validation_workflow(["cpu"]),
        device_id="system",
    )

    assert execution["report"].status == "incomplete"
    assert execution["session"]["status"] == "incomplete"
    assert execution["report"].data["asset"]["manufacturer"] == "Acme"
    assert execution["report"].data["technician_record"]
    assert execution["report"].data["selected_diagnostics"] == ["cpu", "memory"]
    assert execution["report"].data["workflow_result"].success is True


def test_empty_planned_session_cannot_be_marked_checks_complete(
    sqlite_settings,
):
    database = SQLiteDatabase(sqlite_settings / "uhdp.sqlite3")
    service = DiagnosticSessionService()
    service._repository = SQLiteSessionRepository(database)
    service._sessions = {}
    session = service.create_session(
        intake_record={"planned_diagnostics": ["cpu"]},
    )

    completed = service.complete_session(session["session_id"])

    assert completed["status"] == "incomplete"
    assert completed["report"].status == "incomplete"


def test_sqlite_legacy_import_is_idempotent_and_preserves_sources(tmp_path):
    sessions = tmp_path / "legacy-sessions"
    reports = tmp_path / "legacy-reports"
    sessions.mkdir()
    reports.mkdir()
    session_path = sessions / "session-old.json"
    report_path = reports / "report-old.json"
    session_path.write_text(
        json.dumps({"session_id": "session-old", "status": "incomplete"}),
        encoding="utf-8",
    )
    report_path.write_text(
        json.dumps({"report_id": "report-old", "status": "incomplete"}),
        encoding="utf-8",
    )
    source_hashes = {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (session_path, report_path)
    }
    database = SQLiteDatabase(tmp_path / "legacy.sqlite3")

    first = import_legacy_files(database, [sessions], [reports])
    repeated = import_legacy_files(database, [sessions], [reports])

    assert first == {"sessions": 1, "reports": 1, "skipped": 0}
    assert repeated == {"sessions": 0, "reports": 0, "skipped": 2}
    assert database.get_session("session-old")["status"] == "incomplete"
    assert database.get_report_json("report-old")["status"] == "incomplete"
    assert source_hashes == {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (session_path, report_path)
    }


def test_legacy_sqlite_report_storage_preserves_evaluation_in_json_and_html(
    sqlite_settings,
):
    database = SQLiteDatabase(sqlite_settings / "uhdp.sqlite3")
    storage = SQLiteReportStorage(database)
    diagnostic_result = DiagnosticResult(
        diagnostic_id="cpu",
        diagnostic_type="cpu",
        device_id="device-legacy",
        status="passed",
        evaluation={
            "status": "inconclusive",
            "warnings": ["Inventory is not a functional check"],
        },
        details={"logical_cores": 8},
    )
    session = SimpleNamespace(
        session_id="legacy-session",
        device_id="device-legacy",
        started_at=datetime.now(UTC),
        completed_at=None,
        results={"cpu": diagnostic_result},
    )
    report = ReportGenerator().generate(session)
    storage.save(report)

    report_json = storage.get_json(session.session_id)
    report_html = storage.get_html(session.session_id)

    assert report_json is not None
    assert report_html is not None
    assert report_json["overall_status"] == "INCOMPLETE"
    assert report_json["results"]["cpu"]["evaluation"]["status"] == (
        "inconclusive"
    )
    assert report_json["results"]["cpu"]["details"]["logical_cores"] == 8
    assert "INCOMPLETE" in report_html
    assert "inconclusive" in report_html
    assert "PASS" not in report_html


def test_asset_without_identity_keeps_identity_fields_unknown(sqlite_settings):
    database = SQLiteDatabase(sqlite_settings / "uhdp.sqlite3")
    service = DiagnosticSessionService()
    service._repository = SQLiteSessionRepository(database)
    service._sessions = {}

    session = service.create_session(
        device_id="unknown",
        session_id=str(uuid4()),
        intake_record={"create_asset": True, "asset_tag": "UNIDENTIFIED"},
    )

    asset = database.get_asset(session["asset_id"])

    assert asset is not None
    assert asset["asset_tag"] == "UNIDENTIFIED"
    assert asset.get("manufacturer") is None
    assert asset.get("model") is None
    assert asset.get("serial_number") is None


def test_sqlite_serializes_concurrent_writes_without_losing_sessions(tmp_path):
    database = SQLiteDatabase(tmp_path / "concurrent.sqlite3")

    def save(index: int) -> None:
        session_id = f"session-{index}"
        database.save_session(
            session_id,
            {"session_id": session_id, "status": "created"},
            enqueue_sync=False,
        )

    with ThreadPoolExecutor(max_workers=6) as executor:
        list(executor.map(save, range(12)))

    assert len(database.list_sessions()) == 12
    with database.connection() as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
