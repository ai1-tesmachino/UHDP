from pathlib import Path

from app.workflows.reporting.diagnostic_report import (
    DiagnosticReport,
)
from app.workflows.reporting.file_report_repository import (
    FileReportRepository,
)


def test_save_report(
    tmp_path,
):

    repository = (
        FileReportRepository(
            tmp_path,
        )
    )

    report = DiagnosticReport(
        data={
            "cpu": "ok",
        }
    )

    repository.save(
        "report1",
        report,
    )

    report_file = (
        Path(tmp_path)
        / "report1.json"
    )

    assert report_file.exists()