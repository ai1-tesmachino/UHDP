import json

import pytest

from app.hal.diagnostic_result import DiagnosticResult
from app.hal.diagnostic_status import DiagnosticStatus
from app.workflows.reporting.diagnostic_report import (
    DiagnosticReport,
)
from app.workflows.reporting.file_report_repository import (
    FileReportRepository,
)


def test_save_report(tmp_path):

    result = DiagnosticResult(
        diagnostic_id="cpu-001",
        diagnostic_type="cpu",
        device_id="device-001",
        status=DiagnosticStatus.PASSED,
        message="CPU passed",
        details={
            "cores": 8,
        },
    )

    report = DiagnosticReport(
        report_id="report-001",
        device_id="device-001",
        status="passed",
        data={
            "cpu_result": result,
        },
    )

    repository = FileReportRepository(
        tmp_path
    )

    repository.save(
        "test-report",
        report,
    )

    file_path = (
        tmp_path
        / "test-report.json"
    )

    assert file_path.exists()

    with open(
        file_path,
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    assert data["report_id"] == "report-001"
    assert data["device_id"] == "device-001"
    assert data["status"] == "passed"

    assert (
        data["data"]["cpu_result"]["diagnostic_id"]
        == "cpu-001"
    )

    assert (
        data["data"]["cpu_result"]["status"]
        == "passed"
    )

    assert (
        data["data"]["cpu_result"]["details"]["cores"]
        == 8
    )


def test_file_report_revisions_are_immutable_and_explicitly_supersedable(tmp_path):
    repository = FileReportRepository(tmp_path)
    first = DiagnosticReport(
        report_id="stable-report",
        revision_id="revision-one",
        session_id="session-one",
        status="passed",
        data={"summary": "original"},
    )
    repository.save("report-one", first)
    repository.finalize_revision("report-one", first.revision_id, "QA")

    changed_same_revision = DiagnosticReport(
        report_id="stable-report",
        revision_id="revision-one",
        session_id="session-one",
        status="failed",
        data={"summary": "changed"},
    )
    with pytest.raises(ValueError, match="already exists"):
        repository.save("report-one", changed_same_revision)

    correction = DiagnosticReport(
        report_id="stable-report",
        revision_id="revision-two",
        supersedes_revision_id="revision-one",
        supersession_reason="Documented QC correction",
        superseded_by="QA",
        session_id="session-one",
        status="passed",
        data={"summary": "corrected"},
    )
    repository.save("report-one", correction)

    history = repository.list_revisions("report-one")
    assert [item["revision_id"] for item in history] == [
        "revision-one",
        "revision-two",
    ]
    assert history[0]["report_id"] == history[1]["report_id"] == "stable-report"
    assert history[0]["finalized_at"]
    assert history[1]["supersedes_revision_id"] == "revision-one"