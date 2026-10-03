import json
from dataclasses import asdict
from dataclasses import is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any
from app.core.config import get_settings
from app.workflows.reporting.diagnostic_report import (
    DiagnosticReport,
)
from app.workflows.reporting.report_repository import (
    ReportRepository,
)


class FileReportRepository(
    ReportRepository,
):

    def __init__(
        self,
        directory: str | Path | None = None,
    ) -> None:

        settings = get_settings()

        self._directory = Path(
            directory
            or settings.REPORTS_DIRECTORY
        )

        self._directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def save(
        self,
        report_name: str,
        report: DiagnosticReport,
    ) -> None:

        self.save_json(
            report_name,
            report,
        )

        self.save_html(
            report_name,
            report,
        )

    def save_json(
        self,
        report_name: str,
        report: DiagnosticReport,
    ) -> None:

        file_path = (
            self._directory
            / f"{report_name}.json"
        )

        serializable_report = (
            self._create_report_payload(
                report
            )
        )

        with open(
            file_path,
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                serializable_report,
                file,
                indent=4,
                default=str,
            )

    def save_html(
        self,
        report_name: str,
        report: DiagnosticReport,
    ) -> None:

        file_path = (
            self._directory
            / f"{report_name}.html"
        )

        html = self._build_html(
            report
        )

        with open(
            file_path,
            "w",
            encoding="utf-8",
        ) as file:

            file.write(
                html
            )

    def get_json(
        self,
        report_name: str,
    ) -> dict | None:

        file_path = (
            self._directory
            / f"{report_name}.json"
        )

        if not file_path.exists():
            return None

        with open(
            file_path,
            "r",
            encoding="utf-8",
        ) as file:

            return json.load(
                file
            )

    def get_html(
        self,
        report_name: str,
    ) -> str | None:

        file_path = (
            self._directory
            / f"{report_name}.html"
        )

        if not file_path.exists():
            return None

        with open(
            file_path,
            "r",
            encoding="utf-8",
        ) as file:

            return file.read()

    def list_reports(
        self,
    ) -> list[str]:

        reports = []

        for file in self._directory.glob(
            "*.json"
        ):
            reports.append(
                file.stem
            )

        reports.sort()

        return reports

    def _create_report_payload(
        self,
        report: DiagnosticReport,
    ) -> dict:

        return {
            "report_id": report.report_id,
            "device_id": report.device_id,
            "status": report.status,
            "created_at": (
                report.created_at.isoformat()
            ),
            "data": self._serialize(
                report.data
            ),
        }

    def _build_html(
        self,
        report: DiagnosticReport,
    ) -> str:

        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>UHDP Diagnostic Report</title>
</head>
<body>

<h1>UHDP Diagnostic Report</h1>

<p><strong>Report ID:</strong> {report.report_id}</p>
<p><strong>Device ID:</strong> {report.device_id}</p>
<p><strong>Status:</strong> {report.status}</p>
<p><strong>Created:</strong> {report.created_at}</p>

<pre>{json.dumps(
    self._serialize(report.data),
    indent=4,
    default=str,
)}</pre>

</body>
</html>
"""

    def _serialize(
        self,
        value: Any,
    ) -> Any:

        if isinstance(
            value,
            Enum,
        ):
            return value.value

        if is_dataclass(
            value
        ):
            return self._serialize(
                asdict(value)
            )

        if isinstance(
            value,
            dict,
        ):
            return {
                key: self._serialize(item)
                for key, item in value.items()
            }

        if isinstance(
            value,
            list,
        ):
            return [
                self._serialize(item)
                for item in value
            ]

        if isinstance(
            value,
            tuple,
        ):
            return [
                self._serialize(item)
                for item in value
            ]

        return value