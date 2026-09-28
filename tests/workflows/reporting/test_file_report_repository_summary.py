import json

from app.hal.diagnostic_result import DiagnosticResult
from app.hal.diagnostic_status import DiagnosticStatus
from app.workflows.reporting.diagnostic_report import (
    DiagnosticReport,
)
from app.workflows.reporting.file_report_repository import (
    FileReportRepository,
)
from app.workflows.reporting.report_builder import (
    ReportBuilder,
)
from app.workflows.workflow_context import (
    WorkflowContext,
)


def make_result(
    diagnostic_id: str,
    diagnostic_type: str,
    status: DiagnosticStatus,
) -> DiagnosticResult:
    return DiagnosticResult(
        diagnostic_id=diagnostic_id,
        diagnostic_type=diagnostic_type,
        device_id="device-1",
        status=status,
        message="test",
    )


def test_report_summary_is_persisted(
    tmp_path,
):
    context = WorkflowContext()

    context.set(
        "device_id",
        "device-1",
    )

    context.set(
        "cpu_result",
        make_result(
            "cpu-1",
            "cpu",
            DiagnosticStatus.PASSED,
        ),
    )

    context.set(
        "memory_result",
        make_result(
            "memory-1",
            "memory",
            DiagnosticStatus.FAILED,
        ),
    )

    report = ReportBuilder().build(context)

    repository = FileReportRepository(
        tmp_path
    )

    repository.save(
        "test_report",
        report,
    )

    report_file = (
        tmp_path / "test_report.json"
    )

    assert report_file.exists()

    with open(
        report_file,
        "r",
        encoding="utf-8",
    ) as file:
        saved = json.load(file)

    assert saved["report_id"] == report.report_id
    assert saved["device_id"] == "device-1"
    assert saved["status"] == "failed"

    summary = saved["data"][
        "diagnostic_summary"
    ]

    assert summary["total"] == 2
    assert summary["passed"] == 1
    assert summary["failed"] == 1
    assert summary["errors"] == 0


def test_report_results_are_persisted(
    tmp_path,
):
    report = DiagnosticReport(
        device_id="device-1",
        status="passed",
        data={
            "cpu_result": make_result(
                "cpu-1",
                "cpu",
                DiagnosticStatus.PASSED,
            )
        },
    )

    repository = FileReportRepository(
        tmp_path
    )

    repository.save(
        "cpu_report",
        report,
    )

    with open(
        tmp_path / "cpu_report.json",
        "r",
        encoding="utf-8",
    ) as file:
        saved = json.load(file)

    cpu_result = saved["data"][
        "cpu_result"
    ]

    assert (
        cpu_result["diagnostic_id"]
        == "cpu-1"
    )

    assert (
        cpu_result["diagnostic_type"]
        == "cpu"
    )

    assert (
        cpu_result["device_id"]
        == "device-1"
    )

    assert (
        cpu_result["status"]
        == "passed"
    )