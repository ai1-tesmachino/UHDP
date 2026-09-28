from app.hal.diagnostic_result import DiagnosticResult
from app.hal.diagnostic_status import DiagnosticStatus
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


def test_report_contains_diagnostic_summary():
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

    summary = report.data[
        "diagnostic_summary"
    ]

    assert summary.total == 2
    assert summary.passed == 1
    assert summary.failed == 1
    assert summary.errors == 0


def test_report_status_uses_diagnostic_results():
    context = WorkflowContext()

    context.set(
        "cpu_result",
        make_result(
            "cpu-1",
            "cpu",
            DiagnosticStatus.PASSED,
        ),
    )

    context.set(
        "storage_result",
        make_result(
            "storage-1",
            "storage",
            DiagnosticStatus.ERROR,
        ),
    )

    report = ReportBuilder().build(context)

    assert (
        report.status
        == DiagnosticStatus.ERROR.value
    )


def test_empty_report_is_pending():
    context = WorkflowContext()

    report = ReportBuilder().build(context)

    summary = report.data[
        "diagnostic_summary"
    ]

    assert summary.total == 0
    assert summary.passed == 0
    assert summary.failed == 0
    assert summary.errors == 0

    assert (
        report.status
        == DiagnosticStatus.PENDING.value
    )