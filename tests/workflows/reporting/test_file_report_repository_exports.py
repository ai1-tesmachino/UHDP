from app.workflows.reporting.diagnostic_report import (
    DiagnosticReport,
)
from app.workflows.reporting.file_report_repository import (
    FileReportRepository,
)


def test_save_json_and_html(
    tmp_path,
):

    repository = (
        FileReportRepository(
            directory=tmp_path,
        )
    )

    report = DiagnosticReport(
        device_id="device-1",
        status="PASSED",
        data={
            "cpu": "PASS",
        },
    )

    repository.save(
        "report-1",
        report,
    )

    json_report = (
        repository.get_json(
            "report-1"
        )
    )

    html_report = (
        repository.get_html(
            "report-1"
        )
    )

    assert json_report is not None
    assert html_report is not None

    assert (
        json_report["device_id"]
        == "device-1"
    )

    assert (
        "UHDP Diagnostic Report"
        in html_report
    )


def test_list_reports(
    tmp_path,
):

    repository = (
        FileReportRepository(
            directory=tmp_path,
        )
    )

    repository.save(
        "report-1",
        DiagnosticReport(),
    )

    repository.save(
        "report-2",
        DiagnosticReport(),
    )

    reports = (
        repository.list_reports()
    )

    assert len(
        reports
    ) == 2

    assert "report-1" in reports
    assert "report-2" in reports