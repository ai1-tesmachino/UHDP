import json
import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.sessions import diagnostic_routes
from app.core.config import get_settings
from app.core.local_reopen_auth import (
    LocalReopenAuthorizer,
    create_credential_hash,
    verify_credential,
)
from app.persistence.local.database import SQLiteDatabase
from app.persistence.repository_factory import create_report_repository
from app.services.diagnostic_session_service import DiagnosticSessionService


@pytest.fixture
def local_reopen_api(monkeypatch, tmp_path):
    credential = "offline supervisor credential"
    credential_hash = create_credential_hash(credential)
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("SESSIONS_DIRECTORY", str(tmp_path / "sessions"))
    monkeypatch.setenv("REPORTS_DIRECTORY", str(tmp_path / "reports"))
    monkeypatch.setenv("SQLITE_DATABASE_PATH", str(tmp_path / "audit.sqlite3"))
    monkeypatch.setenv("STORAGE_BACKEND", "file")
    credential_directory = tmp_path / "data" / "local_auth"
    credential_directory.mkdir(parents=True)
    credential_path = credential_directory / "supervisor.credential"
    credential_path.write_text(credential_hash, encoding="utf-8")
    credential_directory.chmod(0o700)
    credential_path.chmod(0o600)
    get_settings.cache_clear()
    SQLiteDatabase(tmp_path / "audit.sqlite3")

    service = DiagnosticSessionService()
    monkeypatch.setattr(diagnostic_routes, "diagnostic_session_service", service)
    monkeypatch.setattr(
        diagnostic_routes,
        "local_reopen_authorizer",
        LocalReopenAuthorizer(),
    )
    app = FastAPI()
    app.include_router(diagnostic_routes.router)
    yield app, service, credential, credential_hash, credential_path, tmp_path
    get_settings.cache_clear()


def create_session(client: TestClient) -> str:
    response = client.post("/diagnostic-sessions/")
    assert response.status_code == 200
    return response.json()["session_id"]


def test_credential_hash_is_salted_and_verifies():
    first = create_credential_hash("offline supervisor credential")
    second = create_credential_hash("offline supervisor credential")

    assert first != second
    assert verify_credential("offline supervisor credential", first)
    assert not verify_credential("incorrect credential", first)


def post_reopen(
    app: FastAPI,
    session_id: str,
    *,
    actor_label: str = "Local Supervisor",
    credential: str | None = "offline supervisor credential",
    peer: str = "127.0.0.1",
    headers: dict[str, str] | None = None,
) -> tuple[TestClient, object]:
    client = TestClient(app, client=(peer, 12345))
    response = client.post(
        f"/diagnostic-sessions/{session_id}/reopen",
        json={"actor_label": actor_label, "credential": credential},
        headers=headers,
    )
    return client, response


def audit_events(database: SQLiteDatabase, session_id: str) -> list[dict]:
    with database.connection() as connection:
        rows = connection.execute(
            """
            SELECT actor_snapshot_json, payload_json, created_at
            FROM audit_events
            WHERE entity_type = 'qc_session'
              AND entity_id = ?
              AND event_type = 'session_reopen'
            ORDER BY created_at, audit_event_id
            """,
            (session_id,),
        ).fetchall()
    return [
        {
            "actor": json.loads(row["actor_snapshot_json"]),
            "payload": json.loads(row["payload_json"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def test_missing_supervisor_configuration_fails_closed_and_is_audited(
    local_reopen_api,
):
    app, service, _, _, credential_path, tmp_path = local_reopen_api
    credential_path.unlink()
    get_settings.cache_clear()
    session_id = service.create_session()["session_id"]

    client, response = post_reopen(app, session_id)
    client.close()

    assert response.status_code == 503
    assert service.get_session(session_id)["status"] == "created"
    events = audit_events(SQLiteDatabase(tmp_path / "audit.sqlite3"), session_id)
    assert events[-1]["payload"]["reason"] == "credential_not_configured"
    assert events[-1]["payload"]["outcome"] == "denied"


def test_malformed_supervisor_configuration_fails_closed(local_reopen_api):
    app, service, _, _, credential_path, tmp_path = local_reopen_api
    credential_path.write_text("invalid-hash", encoding="utf-8")
    session_id = service.create_session()["session_id"]

    client, response = post_reopen(app, session_id)
    client.close()

    assert response.status_code == 503
    assert service.get_session(session_id)["status"] == "created"
    events = audit_events(SQLiteDatabase(tmp_path / "audit.sqlite3"), session_id)
    assert events[-1]["payload"]["reason"] == "credential_configuration_invalid"


def test_arbitrary_actor_label_and_incorrect_credential_do_not_authorize(
    local_reopen_api,
    tmp_path,
):
    app, service, _, _, _, _ = local_reopen_api
    session_id = service.create_session()["session_id"]

    client, response = post_reopen(
        app,
        session_id,
        actor_label="Administrator",
        credential="not the supervisor credential",
    )
    client.close()

    assert response.status_code == 401
    assert service.get_session(session_id)["status"] == "created"
    events = audit_events(SQLiteDatabase(tmp_path / "audit.sqlite3"), session_id)
    assert events[-1]["actor"] == {"actor_label": "Administrator"}
    assert events[-1]["payload"]["authorization_basis"] is None


def test_missing_submitted_credential_does_not_authorize(local_reopen_api):
    app, service, _, _, _, _ = local_reopen_api
    session_id = service.create_session()["session_id"]
    client = TestClient(app, client=("127.0.0.1", 12345))

    response = client.post(
        f"/diagnostic-sessions/{session_id}/reopen",
        json={"actor_label": "Supervisor"},
    )
    client.close()

    assert response.status_code == 401
    assert service.get_session(session_id)["status"] == "created"


def test_missing_audit_database_fails_closed_without_running_a_migration(
    local_reopen_api,
):
    app, service, credential, _, _, tmp_path = local_reopen_api
    session_id = service.create_session()["session_id"]
    database_path = tmp_path / "audit.sqlite3"
    database_path.unlink()

    client, response = post_reopen(app, session_id, credential=credential)
    client.close()

    assert response.status_code == 503
    assert service.get_session(session_id)["status"] == "created"
    assert not database_path.exists()


def test_initialized_audit_database_persists_reopen_across_database_restart(
    local_reopen_api,
    tmp_path,
):
    app, service, credential, _, _, _ = local_reopen_api
    session_id = service.create_session()["session_id"]
    database_path = tmp_path / "audit.sqlite3"
    database_path.unlink()

    # Live startup runs the legacy importer, which initializes this database
    # and its existing audit schema before accepting the first request.
    SQLiteDatabase(database_path)
    client, response = post_reopen(app, session_id, credential=credential)
    client.close()

    reopened_database = SQLiteDatabase(database_path)
    events = audit_events(reopened_database, session_id)
    assert response.status_code == 200
    assert events[-1]["payload"]["outcome"] == "succeeded"
    assert events[-1]["payload"]["authorization_basis"] == (
        "local_supervisor_credential"
    )


def test_valid_supervisor_credential_is_accepted_from_loopback_and_audited(
    local_reopen_api,
    tmp_path,
    caplog,
):
    app, service, credential, _, _, _ = local_reopen_api
    session_id = service.create_session()["session_id"]
    caplog.set_level(logging.DEBUG)

    client, response = post_reopen(app, session_id, credential=credential)
    client.close()

    assert response.status_code == 200
    assert service.get_session(session_id)["status"] == "checks_complete"
    events = audit_events(SQLiteDatabase(tmp_path / "audit.sqlite3"), session_id)
    assert [event["payload"]["outcome"] for event in events] == [
        "authorized",
        "succeeded",
    ]
    assert all(
        event["payload"]["authorization_basis"] == "local_supervisor_credential"
        for event in events
    )
    assert all(event["actor"]["actor_label"] == "Local Supervisor" for event in events)
    assert all(credential not in json.dumps(event) for event in events)
    assert credential not in caplog.text


def test_remote_request_is_rejected_even_with_valid_credential_and_forwarded_loopback(
    local_reopen_api,
    tmp_path,
):
    app, service, credential, _, _, _ = local_reopen_api
    session_id = service.create_session()["session_id"]

    client, response = post_reopen(
        app,
        session_id,
        credential=credential,
        peer="192.0.2.10",
        headers={"X-Forwarded-For": "127.0.0.1"},
    )
    client.close()

    assert response.status_code == 403
    assert service.get_session(session_id)["status"] == "created"
    events = audit_events(SQLiteDatabase(tmp_path / "audit.sqlite3"), session_id)
    assert events[-1]["payload"]["reason"] == "remote_request"
    assert events[-1]["payload"]["outcome"] == "denied"


def test_failed_attempts_are_throttled(local_reopen_api, tmp_path):
    app, service, _, _, _, _ = local_reopen_api
    session_id = service.create_session()["session_id"]
    responses = []
    for _ in range(5):
        client, response = post_reopen(
            app,
            session_id,
            credential="incorrect supervisor credential",
        )
        client.close()
        responses.append(response.status_code)

    assert responses == [401, 401, 401, 401, 429]
    assert service.get_session(session_id)["status"] == "created"
    events = audit_events(SQLiteDatabase(tmp_path / "audit.sqlite3"), session_id)
    assert len(events) == 5
    assert all(event["payload"]["outcome"] == "denied" for event in events)


def test_reopen_does_not_create_or_modify_a_finalized_report_revision(local_reopen_api):
    app, service, credential, _, _, _ = local_reopen_api
    session_id = service.create_session()["session_id"]
    service.update_technician_record(
        session_id,
        {"final_disposition": "Ready for resale", "qa_approver": "QA"},
    )
    service.finalize_session(session_id)
    report_name = f"diagnostic_{session_id}"
    before = create_report_repository().list_revisions(report_name)
    assert before[-1]["finalized_at"] is not None

    client, response = post_reopen(app, session_id, credential=credential)
    client.close()

    after = create_report_repository().list_revisions(report_name)
    assert response.status_code == 200
    assert len(after) == len(before)
    assert after[-1]["revision_id"] == before[-1]["revision_id"]
    assert after[-1]["finalized_at"] == before[-1]["finalized_at"]
    assert service.get_session(session_id)["status"] == "checks_complete"
