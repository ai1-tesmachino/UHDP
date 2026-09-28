from app.hal.diagnostic_result import DiagnosticResult
from app.hal.diagnostic_status import DiagnosticStatus
from app.workflows.reporting.report_builder import (
    ReportBuilder,
)
from app.workflows.workflow_context import (
    WorkflowContext,
)


def make_result(
    diagnostic_type: str,
    status: DiagnosticStatus,
) -> DiagnosticResult:

    return DiagnosticResult(
        diagnostic_id=f"{diagnostic_type}-001",
        diagnostic_type=diagnostic_type,
        device_id="device-001",
        status=status,
        message="test",
    )


def test_build_passed_report():

    context = WorkflowContext()

    context.set(
        "device_id",
        "device-001",
    )

    context.set(
        "cpu_result",
        make_result(
            "cpu",
            DiagnosticStatus.PASSED,
        ),
    )

    context.set(
        "memory_result",
        make_result(
            "memory",
            DiagnosticStatus.PASSED,
        ),
    )

    report = ReportBuilder().build(
        context
    )

    assert report.report_id
    assert report.device_id == "device-001"
    assert report.status == "passed"
    assert "cpu_result" in report.data
    assert "memory_result" in report.data


def test_build_failed_report():

    context = WorkflowContext()

    context.set(
        "device_id",
        "device-001",
    )

    context.set(
        "cpu_result",
        make_result(
            "cpu",
            DiagnosticStatus.PASSED,
        ),
    )

    context.set(
        "memory_result",
        make_result(
            "memory",
            DiagnosticStatus.FAILED,
        ),
    )

    report = ReportBuilder().build(
        context
    )

    assert report.status == "failed"


def test_build_error_report():

    context = WorkflowContext()

    context.set(
        "device_id",
        "device-001",
    )

    context.set(
        "cpu_result",
        make_result(
            "cpu",
            DiagnosticStatus.ERROR,
        ),
    )

    report = ReportBuilder().build(
        context
    )

    assert report.status == "error"


def test_build_empty_report():

    context = WorkflowContext()

    report = ReportBuilder().build(
        context
    )

    assert report.device_id == "unknown-device"
    assert report.status == "pending"
    assert report.data == {}