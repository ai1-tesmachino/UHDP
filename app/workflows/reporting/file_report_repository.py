import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

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
        directory: str | Path = "data/reports",
    ) -> None:
        self._directory = Path(directory)

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

        serializable_report = {
            "report_id": report.report_id,
            "device_id": report.device_id,
            "status": report.status,
            "created_at": report.created_at.isoformat(),
            "data": self._serialize(
                report.data
            ),
        }

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

    def _serialize(
        self,
        value: Any,
    ) -> Any:

        if isinstance(value, Enum):
            return value.value

        if is_dataclass(value):
            return self._serialize(
                asdict(value)
            )

        if isinstance(value, dict):
            return {
                key: self._serialize(item)
                for key, item in value.items()
            }

        if isinstance(value, list):
            return [
                self._serialize(item)
                for item in value
            ]

        if isinstance(value, tuple):
            return [
                self._serialize(item)
                for item in value
            ]

        return value