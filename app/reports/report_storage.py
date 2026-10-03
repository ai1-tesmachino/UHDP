import json
from pathlib import Path

from app.reports.html_report_generator import HtmlReportGenerator
from app.reports.json_report_generator import JsonReportGenerator
from app.reports.report_models import DiagnosticReport


class ReportStorage:

    def __init__(
        self,
        reports_directory: str = "reports",
    ):
        self._reports_directory = Path(
            reports_directory
        )

        self._reports_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._json_generator = JsonReportGenerator()
        self._html_generator = HtmlReportGenerator()

    def save(
        self,
        report: DiagnosticReport,
    ) -> None:

        session_id = report.session_id

        json_path = (
            self._reports_directory
            / f"{session_id}.json"
        )

        html_path = (
            self._reports_directory
            / f"{session_id}.html"
        )

        json_data = self._json_generator.generate(
            report
        )

        html_data = self._html_generator.generate(
            report
        )

        with open(
            json_path,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                json_data,
                file,
                indent=4,
            )

        with open(
            html_path,
            "w",
            encoding="utf-8",
        ) as file:
            file.write(
                html_data
            )

    def get_json(
        self,
        session_id: str,
    ) -> dict | None:

        path = (
            self._reports_directory
            / f"{session_id}.json"
        )

        if not path.exists():
            return None

        with open(
            path,
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(
                file
            )

    def get_html(
        self,
        session_id: str,
    ) -> str | None:

        path = (
            self._reports_directory
            / f"{session_id}.html"
        )

        if not path.exists():
            return None

        with open(
            path,
            "r",
            encoding="utf-8",
        ) as file:
            return file.read()

    def list_reports(
        self,
    ) -> list[str]:

        reports = []

        for file in self._reports_directory.glob(
            "*.json"
        ):
            reports.append(
                file.stem
            )

        reports.sort()

        return reports