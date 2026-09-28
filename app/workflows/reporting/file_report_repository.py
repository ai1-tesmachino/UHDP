import json
from dataclasses import asdict
from pathlib import Path

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
        directory: str | Path = (
            "data/reports"
        ),
    ) -> None:
        self._directory = Path(
            directory,
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

        file_path = (
            self._directory
            / f"{report_name}.json"
        )

        serializable_data = {}

        for (
            key,
            value,
        ) in report.data.items():

            try:
                serializable_data[key] = (
                    asdict(value)
                )

            except Exception:

                if isinstance(
                    value,
                    list,
                ):

                    converted = []

                    for item in value:
                        try:
                            converted.append(
                                asdict(item)
                            )
                        except Exception:
                            converted.append(
                                str(item)
                            )

                    serializable_data[
                        key
                    ] = converted

                else:
                    serializable_data[
                        key
                    ] = str(value)

        with open(
            file_path,
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                serializable_data,
                file,
                indent=4,
                default=str,
            )