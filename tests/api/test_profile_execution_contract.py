from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api import profiles as profile_routes
from app.hal.diagnostic_result import DiagnosticResult
from app.hal.diagnostic_status import DiagnosticStatus
from app.hal.evaluation_status import EvaluationStatus
from app.hal.models.diagnostic_result_collection import DiagnosticResultCollection
from app.main import app
from app.profiles.file_profile_repository import FileProfileRepository
from app.profiles.profile_service import ProfileService
from app.services import diagnostic_session_service as session_module
from app.services.file_session_repository import FileSessionRepository


class FakeDiscovery:
    def discover(self):
        return SimpleNamespace(devices=[])

    def get_device(self, device_id):
        return SimpleNamespace(device_id=device_id)


class DeterministicDiagnosticService:
    def execute(self, diagnostic_type, device_id, parameters=None):
        details = {
            "cpu": {"physical_cores": 4, "logical_cores": 8},
            "memory": {"total_ram_mb": 8192, "available_ram_mb": 4096},
            "storage": {"drives": [{"mountpoint": "/"}]},
            "network": {
                "adapter_count": 1,
                "adapters": [{"name": "eth0", "state": "up"}],
            },
        }[diagnostic_type]
        return DiagnosticResult(
            diagnostic_id=f"{diagnostic_type}-id",
            diagnostic_type=diagnostic_type,
            device_id=device_id,
            status=DiagnosticStatus.PASSED,
            message="deterministic diagnostic fixture",
            details=details,
        )


class MixedOutcomeDiagnosticService(DeterministicDiagnosticService):
    statuses = {
        "cpu": DiagnosticStatus.FAILED,
        "memory": DiagnosticStatus.ERROR,
        "storage": DiagnosticStatus.UNSUPPORTED,
        "network": DiagnosticStatus.CANCELLED,
    }

    def execute(self, diagnostic_type, device_id, parameters=None):
        result = super().execute(diagnostic_type, device_id, parameters)
        result.status = self.statuses[diagnostic_type]
        return result


def test_profile_api_evaluates_persists_and_reports_all_core_diagnostics(
    tmp_path, monkeypatch
):
    session_service = session_module.diagnostic_session_service
    monkeypatch.setattr(
        session_service, "_repository", FileSessionRepository(tmp_path / "sessions")
    )
    monkeypatch.setattr(session_service, "_sessions", {})
    monkeypatch.setattr(session_module, "discovery_service", FakeDiscovery())
    monkeypatch.setattr(
        session_module, "DiagnosticService", DeterministicDiagnosticService
    )

    profile_service = ProfileService(FileProfileRepository(tmp_path / "profiles"))
    profile_service.create_profile(
        "core_qa", ["cpu", "memory", "storage", "network"]
    )
    monkeypatch.setattr(profile_routes, "_service", profile_service)
    monkeypatch.setattr(
        session_module,
        "ProfileService",
        lambda _repository: profile_service,
    )

    with TestClient(app) as client:
        session_id = client.post(
            "/diagnostic-sessions/", json={"device_id": "device-1"}
        ).json()["session_id"]
        response = client.post(
            f"/profiles/core_qa/execute?session_id={session_id}&device_id=device-1",
            json={"diagnostics": ["cpu", "memory", "storage", "network"]},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["session_id"] == session_id
        assert [item["diagnostic_type"] for item in payload["results"]] == [
            "cpu", "memory", "storage", "network"
        ]
        assert [item["status"] for item in payload["results"]] == [
            "inconclusive",
            "inconclusive",
            "inconclusive",
            "inconclusive",
        ]
        assert payload["results"][1]["details"]["total_ram_mb"] == 8192
        assert payload["results"][2]["details"]["drives"] == [
            {"mountpoint": "/"}
        ]
        assert payload["summary"]["passed"] == 0
        assert payload["summary"]["inconclusive"] == 4

        session_service._sessions.pop(session_id)
        restored = session_service.get_session(session_id)
        assert isinstance(restored["diagnostic_results"], DiagnosticResultCollection)
        assert [
            item.evaluation.status
            for item in restored["diagnostic_results"].results
        ] == [
            EvaluationStatus.INCONCLUSIVE,
            EvaluationStatus.INCONCLUSIVE,
            EvaluationStatus.INCONCLUSIVE,
            EvaluationStatus.INCONCLUSIVE,
        ]

        report_response = client.get(
            f"/diagnostic-sessions/{session_id}/report"
        )
        assert report_response.status_code == 200
        report = report_response.json()
        assert report["status"] == "inconclusive"
        assert report["summary"]["passed"] == 0
        assert report["summary"]["inconclusive"] == 4
        assert report["data"]["memory_result"]["details"]["total_ram_mb"] == 8192
        assert (
            report["data"]["storage_result"]["details"]["drives"][0][
                "mountpoint"
            ]
            == "/"
        )


def test_profile_api_preserves_failure_error_unsupported_and_cancelled_outcomes(
    tmp_path, monkeypatch
):
    session_service = session_module.diagnostic_session_service
    monkeypatch.setattr(
        session_service, "_repository", FileSessionRepository(tmp_path / "sessions")
    )
    monkeypatch.setattr(session_service, "_sessions", {})
    monkeypatch.setattr(session_module, "discovery_service", FakeDiscovery())
    monkeypatch.setattr(
        session_module, "DiagnosticService", MixedOutcomeDiagnosticService
    )

    profile_service = ProfileService(FileProfileRepository(tmp_path / "profiles"))
    profile_service.create_profile(
        "outcome_qa", ["cpu", "memory", "storage", "network"]
    )
    monkeypatch.setattr(profile_routes, "_service", profile_service)
    monkeypatch.setattr(
        session_module,
        "ProfileService",
        lambda _repository: profile_service,
    )

    with TestClient(app) as client:
        session_id = client.post(
            "/diagnostic-sessions/", json={"device_id": "device-1"}
        ).json()["session_id"]
        response = client.post(
            f"/profiles/outcome_qa/execute?session_id={session_id}&device_id=device-1",
            json={"diagnostics": ["cpu", "memory", "storage", "network"]},
        )

        assert response.status_code == 200
        assert [item["status"] for item in response.json()["results"]] == [
            "failed", "error", "unsupported", "cancelled"
        ]
        saved = session_service.get_session(session_id)
        assert [
            saved["test_results"][diagnostic]["test_status"]
            for diagnostic in ("cpu", "memory", "storage", "network")
        ] == ["failed", "error", "unsupported", "cancelled"]
        assert saved["report"].status == "error"


def test_profile_api_rejects_diagnostics_outside_profile(tmp_path, monkeypatch):
    class RejectingSessionService:
        def execute_profile(self, **_kwargs):
            raise ValueError(
                "Selected diagnostics must be unique members of the profile"
            )

    service = ProfileService(FileProfileRepository(tmp_path / "profiles"))
    service.create_profile("cpu_only", ["cpu"])
    monkeypatch.setattr(profile_routes, "_service", service)
    monkeypatch.setattr(
        profile_routes, "diagnostic_session_service", RejectingSessionService()
    )

    with TestClient(app) as client:
        response = client.post(
            "/profiles/cpu_only/execute?session_id=session-1&device_id=device-1",
            json={"diagnostics": ["memory"]},
        )

    assert response.status_code == 400
    assert "unique members" in response.json()["detail"]
